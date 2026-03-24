"""
mesh/session.py — SYSTVETAM AgentSession
One session per crew member. Persistent in memory.
Role file injected as system prompt. OpenRouter is the execution plane.

No stubs. Every function executes.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog

from mesh.config import get_settings
from mesh.models import (
    ChatMessage,
    CrewMemberConfig,
    CrewStatus,
    OpenRouterRequest,
    OpenRouterResponse,
    TaskResult,
    TaskResultStatus,
)

logger = structlog.get_logger("agent-mesh.session")


class AgentSessionError(Exception):
    """Raised when an agent session fails in a non-recoverable way."""

    def __init__(self, callsign: str, detail: str):
        self.callsign = callsign
        self.detail = detail
        super().__init__(f"[{callsign}] {detail}")


class AgentSession:
    """
    A single AI agent session bound to one crew member.

    Lifecycle:
        1. __init__ — stores config, sets status to STANDBY
        2. load_role() — reads role file from disk, sets system prompt
        3. execute(task_body) — async OpenRouter call, returns TaskResult
        4. Persists in memory for the lifetime of the mesh service

    The session maintains a sliding conversation window so agents can
    reference prior task context within the same service lifecycle.
    Max history kept at 10 exchanges to bound token cost.
    """

    MAX_HISTORY_TURNS: int = 10

    def __init__(self, config: CrewMemberConfig) -> None:
        self.callsign: str = config.callsign
        self.agt_id: str = config.agt_id
        self.name: str = config.name
        self.department: str = config.department
        self.model: str = config.model
        self.role_file_path: str = config.role_file

        # Set after load_role()
        self.system_prompt: str = ""
        self.loaded: bool = False

        # Runtime state
        self.status: CrewStatus = CrewStatus.STANDBY
        self.tasks_completed: int = 0
        self.last_task_at: datetime | None = None
        self.conversation_history: list[ChatMessage] = []

        # Shared HTTP client — set by registry after init
        self._http_client: httpx.AsyncClient | None = None

    def load_role(self, roles_dir: Path) -> None:
        """
        Read the canonical role file from disk and set it as system prompt.
        Role files are sacred — injected as-is, never modified.

        Raises AgentSessionError if role file is missing or empty.
        """
        role_path = roles_dir / self.role_file_path
        if not role_path.exists():
            raise AgentSessionError(
                self.callsign,
                f"Role file not found: {role_path}. Cannot instantiate session without identity.",
            )

        content = role_path.read_text(encoding="utf-8").strip()
        if not content:
            raise AgentSessionError(
                self.callsign,
                f"Role file is empty: {role_path}. Doctrine violation — every agent needs identity.",
            )

        self.system_prompt = content
        self.loaded = True
        logger.info(
            "session.role_loaded",
            callsign=self.callsign,
            agt_id=self.agt_id,
            role_file=str(role_path),
            prompt_chars=len(content),
        )

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Inject shared HTTP client from registry. One pool for all sessions."""
        self._http_client = client

    async def execute(self, task_body: str, task_id: str = "") -> TaskResult:
        """
        Execute a task against OpenRouter using this agent's identity.

        Flow:
            1. Build messages: system prompt + history + current task
            2. POST to OpenRouter /chat/completions
            3. Extract response text + token usage
            4. Append exchange to conversation history (bounded)
            5. Return TaskResult

        On failure: returns TaskResult with status=FAILED and error detail.
        No silent failures. No phantom completions.
        """
        if not self.loaded:
            raise AgentSessionError(
                self.callsign,
                "Session not loaded. Call load_role() before execute().",
            )

        if self._http_client is None:
            raise AgentSessionError(
                self.callsign,
                "No HTTP client set. Call set_http_client() before execute().",
            )

        settings = get_settings()
        self.status = CrewStatus.EXECUTING
        start_time = time.monotonic()

        log = logger.bind(
            callsign=self.callsign,
            agt_id=self.agt_id,
            model=self.model,
            task_id=task_id,
        )
        log.info("session.execute.start", task_chars=len(task_body))

        # Build message payload
        messages = self._build_messages(task_body)

        request = OpenRouterRequest(
            model=self.model,
            messages=messages,
            max_tokens=settings.max_task_tokens,
            temperature=0.3,
            top_p=0.95,
        )

        try:
            raw_response = await self._call_openrouter(request)
            response = OpenRouterResponse.model_validate(raw_response)

            if not response.choices:
                log.error("session.execute.no_choices", raw=raw_response)
                self.status = CrewStatus.ACTIVE
                return TaskResult(
                    task_id=task_id,
                    callsign=self.callsign,
                    status=TaskResultStatus.FAILED,
                    output="",
                    model_used=self.model,
                    error_detail="OpenRouter returned zero choices.",
                )

            output_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            elapsed = round(time.monotonic() - start_time, 2)

            # Append to bounded conversation history
            self._append_history(task_body, output_text)

            self.tasks_completed += 1
            self.last_task_at = datetime.now(timezone.utc)
            self.status = CrewStatus.ACTIVE

            log.info(
                "session.execute.complete",
                tokens=tokens_used,
                output_chars=len(output_text),
                elapsed_s=elapsed,
            )

            return TaskResult(
                task_id=task_id,
                callsign=self.callsign,
                status=TaskResultStatus.COMPLETED,
                output=output_text,
                tokens_used=tokens_used,
                model_used=self.model,
            )

        except httpx.HTTPStatusError as e:
            elapsed = round(time.monotonic() - start_time, 2)
            error_body = e.response.text[:500] if e.response else "no response body"
            log.error(
                "session.execute.http_error",
                status_code=e.response.status_code if e.response else 0,
                error=error_body,
                elapsed_s=elapsed,
            )
            self.status = CrewStatus.ACTIVE
            return TaskResult(
                task_id=task_id,
                callsign=self.callsign,
                status=TaskResultStatus.FAILED,
                output="",
                model_used=self.model,
                error_detail=f"HTTP {e.response.status_code}: {error_body}",
            )

        except httpx.RequestError as e:
            elapsed = round(time.monotonic() - start_time, 2)
            log.error(
                "session.execute.request_error",
                error=str(e),
                elapsed_s=elapsed,
            )
            self.status = CrewStatus.ACTIVE
            return TaskResult(
                task_id=task_id,
                callsign=self.callsign,
                status=TaskResultStatus.FAILED,
                output="",
                model_used=self.model,
                error_detail=f"Request error: {e}",
            )

        except Exception as e:
            elapsed = round(time.monotonic() - start_time, 2)
            log.error(
                "session.execute.unexpected_error",
                error=str(e),
                elapsed_s=elapsed,
            )
            self.status = CrewStatus.ACTIVE
            return TaskResult(
                task_id=task_id,
                callsign=self.callsign,
                status=TaskResultStatus.FAILED,
                output="",
                model_used=self.model,
                error_detail=f"Unexpected: {e}",
            )

    def _build_messages(self, task_body: str) -> list[ChatMessage]:
        """
        Assemble the message list for OpenRouter.
        System prompt (role file) is always first.
        Conversation history provides multi-turn context.
        Current task is the latest user message.
        """
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt),
        ]
        # Append bounded history
        messages.extend(self.conversation_history)
        # Current task
        messages.append(ChatMessage(role="user", content=task_body))
        return messages

    def _append_history(self, task_body: str, response_text: str) -> None:
        """
        Add the latest exchange to conversation history.
        Bounded at MAX_HISTORY_TURNS exchanges (2 messages each).
        Oldest exchanges evicted first — sliding window.
        """
        self.conversation_history.append(
            ChatMessage(role="user", content=task_body)
        )
        self.conversation_history.append(
            ChatMessage(role="assistant", content=response_text)
        )
        # Trim to max turns (each turn = 2 messages)
        max_messages = self.MAX_HISTORY_TURNS * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    async def _call_openrouter(self, request: OpenRouterRequest) -> dict:
        """
        POST to OpenRouter /chat/completions.
        Uses shared httpx.AsyncClient from registry.
        Raises on HTTP errors — caller handles.
        """
        settings = get_settings()
        url = f"{settings.openrouter_base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://zentrauxgroup.com",
            "X-Title": f"SYSTVETAM-{self.callsign}",
        }

        payload = request.model_dump(mode="json")

        response = await self._http_client.post(  # type: ignore[union-attr]
            url,
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()

    def reset_history(self) -> None:
        """Clear conversation history. Used for fresh task contexts."""
        self.conversation_history.clear()
        logger.info("session.history_reset", callsign=self.callsign)

    def to_health(self) -> dict:
        """Snapshot for /health endpoint."""
        return {
            "callsign": self.callsign,
            "agt_id": self.agt_id,
            "name": self.name,
            "department": self.department,
            "model": self.model,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "last_task_at": self.last_task_at.isoformat() if self.last_task_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"AgentSession(callsign={self.callsign!r}, agt_id={self.agt_id!r}, "
            f"model={self.model!r}, status={self.status.value!r}, "
            f"tasks={self.tasks_completed})"
        )
