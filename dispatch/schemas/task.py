"""
SYSTVETAM — Task Schemas
Zentraux Group LLC

Pydantic models for task API request validation and response serialization.
These are the contract between Central Dispatch and everything that talks to it.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    """POST /tasks — create a new task in state NEW."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    task_type: str = Field("STANDARD", description="Task type enum value")
    department: str | None = Field(None, max_length=50)
    source: str | None = Field("DISPATCH", max_length=50)
    requested_by: str = Field("AGT-001", max_length=50)
    priority: int = Field(3, ge=1, le=5, description="1=CRITICAL, 5=BACKLOG")
    intel_brief_id: uuid.UUID | None = Field(
        None, description="Link to intelligence brief for BUILD_FROM_INTEL tasks"
    )
    payload: dict[str, Any] | None = None


class AssignRequest(BaseModel):
    """PATCH /tasks/{id}/assign — NEW → ASSIGNED."""
    assigned_to: uuid.UUID = Field(..., description="Crew member UUID to assign")
    actor_id: str = Field("AGT-001", max_length=50)


class ExecuteRequest(BaseModel):
    """PATCH /tasks/{id}/execute — ASSIGNED → EXECUTING."""
    actor_id: str = Field("AGT-001", max_length=50)
    execution_plane: str = Field("cloud", pattern="^(cloud|local)$")
    container_id: str | None = Field(None, max_length=80)


class SubmitRequest(BaseModel):
    """PATCH /tasks/{id}/submit — EXECUTING → QA_GATE."""
    actor_id: str = Field("AGT-001", max_length=50)
    output: str | None = Field(None, description="Deliverable content from crew execution")


class QAPassRequest(BaseModel):
    """PATCH /tasks/{id}/qa-pass — QA_GATE → LEVI_GATE."""
    actor_id: str = Field("AGT-001", max_length=50)
    qa_result: dict[str, Any] | None = Field(None, description="SOP-008 evaluation output")


class QAFailRequest(BaseModel):
    """PATCH /tasks/{id}/qa-fail — QA_GATE → EXECUTING. Note required."""
    actor_id: str = Field("AGT-001", max_length=50)
    note: str = Field(..., min_length=1, max_length=2000, description="Reason for QA failure")
    qa_result: dict[str, Any] | None = None


class ApproveRequest(BaseModel):
    """PATCH /tasks/{id}/approve — LEVI_GATE → DEPLOYING."""
    actor_id: str = Field("AGT-001", max_length=50)
    note: str | None = Field(None, max_length=2000)


class ReturnRequest(BaseModel):
    """PATCH /tasks/{id}/return — LEVI_GATE → ASSIGNED. Note required."""
    actor_id: str = Field("AGT-001", max_length=50)
    note: str = Field(..., min_length=1, max_length=2000, description="Reason for return")


class GateActionRequest(BaseModel):
    """POST /gates/{id}/approve or /gates/{id}/return."""
    actor_id: str = Field("AGT-001", max_length=50)
    note: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class TaskResponse(BaseModel):
    """Single task response — used for detail and mutation responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_ref: str
    title: str
    description: str | None = None
    output: str | None = None
    task_type: str
    source: str | None = None
    department: str | None = None
    assigned_to: uuid.UUID | None = None
    requested_by: str
    status: str
    priority: int
    qa_result: dict[str, Any] | None = None
    levi_note: str | None = None
    intel_brief_id: uuid.UUID | None = None
    container_id: str | None = None
    execution_plane: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    assigned_at: datetime | None = None
    executing_at: datetime | None = None
    completed_at: datetime | None = None
    receipted_at: datetime | None = None


class TaskListResponse(BaseModel):
    """Paginated task list response."""
    tasks: list[TaskResponse]
    total: int
    offset: int
    limit: int
