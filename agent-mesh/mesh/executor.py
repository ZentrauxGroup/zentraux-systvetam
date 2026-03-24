"""
mesh/executor.py — SYSTVETAM Task Executor
Receives a routed task + session from the router.
Calls session.execute() → publishes result two ways:
  1. Redis: results:{task_id} — Dispatch subscribes to results:*
  2. HTTP: PATCH {DISPATCH_URL}/tasks/{task_id}/submit — belt and suspenders

No silent failures. Every execution produces a result payload.
If Dispatch HTTP fails after 2 retries, result is still in Redis.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import redis.asyncio as aioredis
import structlog

from mesh.config import get_settings
from mesh.models import TaskPayload, TaskResult, TaskResultStatus

if TYPE_CHECKING:
    from mesh.session import AgentSession

logger = structlog.get_logger("agent-mesh.executor")

# Max retries for Dispatch HTTP callback
MAX_DISPATCH_RETRIES: int = 2
RETRY_DELAY_SECONDS: float = 2.0


class TaskExecutor:
    """
    Executes tasks against agent sessions and delivers results.

    Lifecycle:
        1. start() — open Redis + HTTP connections
        2. run(session, task) — called per task by router (fire-and-forget)
        3. stop() — close connections

    Dual delivery: Redis publish (primary) + HTTP PATCH (confirmation).
    Dispatch consumes from Redis results:* — the HTTP call is a
    redundant confirmation path so nothing slips through.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._http_client: httpx.AsyncClient | None = None

        # Metrics
        self.tasks_executed: int = 0
        self.tasks_failed: int = 0
        self.redis_publish_failures: int = 0
        self.dispatch_post_failures: int = 0

    async def start(self) -> None:
        """Open Redis and HTTP connections."""
        settings = get_settings()

        self._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=10.0,
            socket_timeout=30.0,
        )

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=15.0,
                pool=10.0,
            ),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            ),
        )

        logger.info("executor.started")

    async def run(self, session: AgentSession, task: TaskPayload) -> None:
        """
        Full execution pipeline for a single task:
          1. Call session.execute(task.body, task.task_id)
          2. Publish result to Redis results:{task_id}
          3. PATCH result to Dispatch HTTP endpoint
          4. Log outcome — never raise, never crash the mesh
        """
        log = logger.bind(
            callsign=session.callsign,
            task_id=task.task_id,
            department=task.department,
        )

        log.info(
            "executor.run.start",
            title=task.title[:80],
            priority=task.priority,
        )

        # --- 1. Execute against agent session ---
        try:
            result = await session.execute(
                task_body=self._build_task_prompt(task),
                task_id=task.task_id,
            )
        except Exception as e:
            # Session.execute should never raise (it returns FAILED status),
            # but we catch anyway — the mesh must not crash.
            log.error("executor.run.session_error", error=str(e))
            result = TaskResult(
                task_id=task.task_id,
                callsign=session.callsign,
                status=TaskResultStatus.FAILED,
                output="",
                model_used=session.model,
                error_detail=f"Session error: {e}",
            )

        if result.status == TaskResultStatus.COMPLETED:
            self.tasks_executed += 1
        else:
            self.tasks_failed += 1

        log.info(
            "executor.run.result",
            status=result.status,
            tokens=result.tokens_used,
            output_chars=len(result.output),
        )

        # --- 2. Publish to Redis (primary delivery path) ---
        await self._publish_redis(result, log)

        # --- 3. PATCH to Dispatch (confirmation path) ---
        await self._patch_dispatch(result, log)

    def _build_task_prompt(self, task: TaskPayload) -> str:
        """
        Format the task payload into a clear prompt for the agent.
        Includes metadata so the agent knows context.
        """
        lines = [
            f"## TASK ASSIGNMENT — {task.title}",
            f"**Task ID:** {task.task_id}",
            f"**Priority:** {task.priority}",
            f"**Department:** {task.department}",
            f"**Requested by:** {task.requester}",
            f"**Issued:** {task.issued_at.isoformat()}",
            "",
            "---",
            "",
            task.body,
        ]
        return "\n".join(lines)

    async def _publish_redis(
        self,
        result: TaskResult,
        log: structlog.stdlib.BoundLogger,
    ) -> None:
        """
        Publish result to Redis results:{task_id}.
        Dispatch subscribes to results:* and updates task state machine.
        """
        if self._redis is None:
            log.error("executor.redis.not_connected")
            self.redis_publish_failures += 1
            return

        channel = f"results:{result.task_id}"
        payload = result.model_dump_json()

        try:
            receivers = await self._redis.publish(channel, payload)
            log.info(
                "executor.redis.published",
                channel=channel,
                receivers=receivers,
                payload_bytes=len(payload),
            )
        except Exception as e:
            self.redis_publish_failures += 1
            log.error(
                "executor.redis.publish_failed",
                channel=channel,
                error=str(e),
            )

    async def _patch_dispatch(
        self,
        result: TaskResult,
        log: structlog.stdlib.BoundLogger,
    ) -> None:
        """
        PATCH result to Dispatch HTTP endpoint.
        Retries up to MAX_DISPATCH_RETRIES times on failure.
        This is the confirmation path — Redis is primary.
        """
        if self._http_client is None:
            log.error("executor.dispatch.no_http_client")
            self.dispatch_post_failures += 1
            return

        settings = get_settings()
        url = f"{settings.dispatch_url}/tasks/{result.task_id}/submit"
        headers = self._dispatch_headers()
        payload = result.model_dump(mode="json")

        for attempt in range(1, MAX_DISPATCH_RETRIES + 1):
            try:
                response = await self._http_client.patch(
                    url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                log.info(
                    "executor.dispatch.patched",
                    url=url,
                    status_code=response.status_code,
                    attempt=attempt,
                )
                return  # Success — exit retry loop

            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response else 0
                body = e.response.text[:300] if e.response else ""
                log.warning(
                    "executor.dispatch.http_error",
                    url=url,
                    status_code=status,
                    body=body,
                    attempt=attempt,
                    max_retries=MAX_DISPATCH_RETRIES,
                )

            except httpx.RequestError as e:
                log.warning(
                    "executor.dispatch.request_error",
                    url=url,
                    error=str(e),
                    attempt=attempt,
                    max_retries=MAX_DISPATCH_RETRIES,
                )

            # Wait before retry (skip wait on last attempt)
            if attempt < MAX_DISPATCH_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

        # All retries exhausted
        self.dispatch_post_failures += 1
        log.error(
            "executor.dispatch.exhausted",
            url=url,
            task_id=result.task_id,
            retries=MAX_DISPATCH_RETRIES,
            note="Result is in Redis — Dispatch can recover from results:* subscription",
        )

    def _dispatch_headers(self) -> dict[str, str]:
        """Auth headers for Dispatch API calls."""
        settings = get_settings()
        headers = {
            "Content-Type": "application/json",
            "X-Service": "agent-mesh",
            "X-Mesh-Version": "0.1.0",
        }
        if settings.mesh_service_token:
            headers["Authorization"] = f"Bearer {settings.mesh_service_token}"
        return headers

    async def stop(self) -> None:
        """Close Redis and HTTP connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self._redis:
            await self._redis.close()
            self._redis = None

        logger.info(
            "executor.stopped",
            tasks_executed=self.tasks_executed,
            tasks_failed=self.tasks_failed,
            redis_failures=self.redis_publish_failures,
            dispatch_failures=self.dispatch_post_failures,
        )

    def stats(self) -> dict:
        """Executor metrics for /health."""
        return {
            "tasks_executed": self.tasks_executed,
            "tasks_failed": self.tasks_failed,
            "redis_publish_failures": self.redis_publish_failures,
            "dispatch_post_failures": self.dispatch_post_failures,
        }
