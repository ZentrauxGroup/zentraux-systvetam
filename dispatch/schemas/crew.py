"""
SYSTVETAM — Crew Schemas
Zentraux Group LLC

Pydantic response models for the crew roster API.
Crew members are seeded from canonical role files — no create endpoint.
Updates happen via container lifecycle and task assignment, not direct API.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from dispatch.schemas.task import TaskResponse


class CrewMemberResponse(BaseModel):
    """Single crew member response with live status."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    callsign: str
    display_name: str
    role: str
    department: str
    sop_reference: str | None = None
    execution_plane: str
    container_image: str | None = None
    container_port: int | None = None
    status: str
    container_id: str | None = None
    current_task_ref: str | None = None
    last_heartbeat: datetime | None = None
    bio: str | None = None
    created_at: datetime


class CrewMemberDetailResponse(CrewMemberResponse):
    """Crew member with active tasks included — used for detail endpoint."""
    active_tasks: list[TaskResponse] = []


class CrewListResponse(BaseModel):
    """Crew roster response."""
    crew: list[CrewMemberResponse]
    total: int
    active_count: int
    executing_count: int
