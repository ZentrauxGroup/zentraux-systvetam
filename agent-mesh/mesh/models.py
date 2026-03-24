"""
mesh/models.py — SYSTVETAM Agent Mesh Data Schemas
All payloads that cross service boundaries are defined here.
No implicit structures. No untyped dicts in production.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---

class TaskPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskResultStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class CrewStatus(StrEnum):
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    OFFLINE = "OFFLINE"
    EXECUTING = "EXECUTING"


class MeshStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


# --- Task Payload (received from Central Dispatch via Redis) ---

class TaskPayload(BaseModel):
    """
    Published by Central Dispatch to dept:{department} channel
    when a task transitions to EXECUTING.
    """
    task_id: str
    callsign: str
    department: str
    title: str
    body: str
    priority: TaskPriority = TaskPriority.MEDIUM
    requester: str = "AGT-001"
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Task Result (published back to Dispatch via Redis) ---

class TaskResult(BaseModel):
    """
    Published by agent-mesh to results:{task_id} channel
    after agent execution completes.
    """
    task_id: str
    callsign: str
    status: TaskResultStatus
    output: str
    tokens_used: int = 0
    model_used: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_detail: str | None = None


# --- Heartbeat (PATCH to Dispatch /crew/{callsign}/status) ---

class HeartbeatPayload(BaseModel):
    """Sent every 30 seconds per session to Central Dispatch."""
    status: CrewStatus
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Health Response ---

class SessionHealth(BaseModel):
    """Individual session status for health endpoint."""
    callsign: str
    agt_id: str
    name: str
    department: str
    model: str
    status: CrewStatus
    tasks_completed: int = 0
    last_task_at: datetime | None = None


class HealthResponse(BaseModel):
    """GET /health response — full mesh snapshot."""
    status: MeshStatus
    sessions: int
    mesh: str = "ACTIVE"
    zos_env: str
    uptime_seconds: float
    sessions_detail: list[SessionHealth] = []


# --- OpenRouter Request/Response Schemas ---

class ChatMessage(BaseModel):
    """Single message in OpenRouter chat completion."""
    role: str
    content: str


class OpenRouterRequest(BaseModel):
    """Request body for OpenRouter /chat/completions."""
    model: str
    messages: list[ChatMessage]
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.95


class OpenRouterChoice(BaseModel):
    """Single choice from OpenRouter response."""
    message: ChatMessage
    finish_reason: str | None = None


class OpenRouterUsage(BaseModel):
    """Token usage from OpenRouter response."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenRouterResponse(BaseModel):
    """Response from OpenRouter /chat/completions."""
    id: str = ""
    choices: list[OpenRouterChoice] = []
    usage: OpenRouterUsage = OpenRouterUsage()
    model: str = ""


# --- Crew Member Config (used by SessionRegistry at init) ---

class CrewMemberConfig(BaseModel):
    """
    Derived from CREW_REGISTRY in config.py.
    Carries everything needed to instantiate an AgentSession.
    """
    agt_id: str
    callsign: str
    name: str
    department: str
    role_file: str
    model: str


# --- Error Schemas ---

class MeshError(BaseModel):
    """Standard error response from agent-mesh endpoints."""
    error: str
    detail: str | None = None
    callsign: str | None = None
    task_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
