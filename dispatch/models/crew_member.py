"""
SYSTVETAM — Crew Member Model
Zentraux Group LLC

The 16-member crew exists as role files in canonical/roles/.
This model makes them addressable in the database — assignable to tasks,
trackable by status, and visible in the Tower Dashboard crew roster.

Each crew member maps to an on-demand Docker container.
When a task is assigned, the container spins up under role file identity,
executes, posts output to Central Dispatch, and shuts down.

Status lifecycle:
  IDLE → EXECUTING → IDLE          (normal task cycle)
  IDLE → EXECUTING → ERROR → IDLE  (container failure, recovery)
  Any  → OFFLINE                   (manual deactivation)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dispatch.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CrewStatus(str, enum.Enum):
    """Crew member operational status — visible as pulse state in Tower Dashboard."""
    ACTIVE = "ACTIVE"       # Online, no current task
    IDLE = "IDLE"           # Online, waiting for assignment
    EXECUTING = "EXECUTING" # Gold pulse — task in progress
    ERROR = "ERROR"         # Red pulse — container failure
    OFFLINE = "OFFLINE"     # Deactivated — no pulse


class ExecutionPlane(str, enum.Enum):
    """Which inference backend this crew member uses by default."""
    CLOUD = "cloud"   # Plane A: OpenRouter → Claude Sonnet 4.6
    LOCAL = "local"   # Plane B: Ollama → qwen3:8b


# ---------------------------------------------------------------------------
# CrewMember ORM Model
# ---------------------------------------------------------------------------

class CrewMember(Base):
    __tablename__ = "crew_members"

    # --- Identity ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    callsign: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Lowercase hyphenated: jordan-reese, marcus-reed, etc.",
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable: Jordan Reese, Marcus Reed, etc.",
    )

    # --- Role & Department ---
    role: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Primary role title from canonical role file",
    )
    department: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ENGINEERING, SALES, INTELLIGENCE, FINANCE, etc.",
    )
    sop_reference: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Primary SOP this crew member operates under",
    )

    # --- Execution Configuration ---
    execution_plane: Mapped[ExecutionPlane] = mapped_column(
        Enum(ExecutionPlane, name="execution_plane", create_constraint=True),
        nullable=False,
        default=ExecutionPlane.CLOUD,
        comment="Default inference backend — cloud or local",
    )
    container_image: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Docker image name for this crew member's container",
    )
    container_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Exposed port when container is running",
    )

    # --- Live State ---
    status: Mapped[CrewStatus] = mapped_column(
        Enum(CrewStatus, name="crew_status", create_constraint=True),
        nullable=False,
        default=CrewStatus.IDLE,
        index=True,
    )
    container_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        comment="Active Docker container ID when EXECUTING",
    )
    current_task_ref: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="ZG-ref of currently executing task",
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last container health check response",
    )

    # --- Metadata ---
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short bio from canonical role file",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # --- Relationships ---
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="crew_member",
        lazy="selectin",
        foreign_keys="Task.assigned_to",
    )

    # --- Indexes ---
    __table_args__ = (
        Index("ix_crew_department_status", "department", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CrewMember {self.callsign} "
            f"status={self.status.value} "
            f"dept={self.department}>"
        )
