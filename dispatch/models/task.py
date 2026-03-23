"""
SYSTVETAM — Task Model
Zentraux Group LLC

The Task is the atomic unit of work in the Systvetam.
Every task travels the state machine. No shortcuts. No bypasses.
The machine IS the doctrine.

Status enforcement: PostgreSQL CHECK constraint.
Application code cannot write an invalid status.
Only state_machine.py may advance status — this model defines the schema.

Status Flow (v1.0 + Addendum v1.1):
  NEW → ASSIGNED → EXECUTING → QA_GATE → LEVI_GATE → DEPLOYING → COMPLETE → RECEIPTED
                                  ↓ FAIL      ↓ RETURN
                               EXECUTING    ASSIGNED
  Any state → FAILED (terminal — container error, unrecoverable)

Task Types (v1.0 + Addendum A5 — Product Factory Loop):
  STANDARD           — default crew task
  INTELLIGENCE_BRIEF — originated from Clyde sweep
  BUILD_FROM_INTEL   — engineering build from approved intel brief
  OPPORTUNITY        — business opportunity from intel pipeline
  GTM_CAMPAIGN       — go-to-market execution (Jordan's world)
  VOICE_OUTREACH     — ElevenLabs voice outreach task
  SECURITY_REVIEW    — Jax security audit
  QA_EVALUATION      — Riley QA gate execution
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dispatch.database import Base


# ---------------------------------------------------------------------------
# Enums — defined in Python, enforced in PostgreSQL
# ---------------------------------------------------------------------------

class TaskStatus(str, enum.Enum):
    """
    State machine positions. Transition rules live in state_machine.py.
    DB CHECK constraint prevents any value outside this enum.
    """
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    QA_GATE = "QA_GATE"
    LEVI_GATE = "LEVI_GATE"
    DEPLOYING = "DEPLOYING"
    COMPLETE = "COMPLETE"
    RECEIPTED = "RECEIPTED"
    FAILED = "FAILED"


class TaskType(str, enum.Enum):
    """
    Task origin / category. Determines routing and floor visibility.
    Extended by Addendum A5 for the Product Factory Loop.
    """
    STANDARD = "STANDARD"
    INTELLIGENCE_BRIEF = "INTELLIGENCE_BRIEF"
    BUILD_FROM_INTEL = "BUILD_FROM_INTEL"
    OPPORTUNITY = "OPPORTUNITY"
    GTM_CAMPAIGN = "GTM_CAMPAIGN"
    VOICE_OUTREACH = "VOICE_OUTREACH"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    QA_EVALUATION = "QA_EVALUATION"


class TaskPriority(int, enum.Enum):
    """Priority levels — lower number = higher urgency."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKLOG = 5


# ---------------------------------------------------------------------------
# Task ORM Model
# ---------------------------------------------------------------------------

class Task(Base):
    __tablename__ = "tasks"

    # --- Identity ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_ref: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment="Human-readable ref: ZG-NNNN",
    )

    # --- Content ---
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Final deliverable content from crew execution",
    )

    # --- Classification ---
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", create_constraint=True),
        nullable=False,
        default=TaskType.STANDARD,
    )
    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Origin system: DISPATCH, CLYDE, MANUAL, DISCORD",
    )
    department: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Department: ENGINEERING, SALES, INTELLIGENCE, etc.",
    )

    # --- Assignment ---
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="AGT-001",
        comment="Agent ID of requester — default is Levi",
    )

    # --- State Machine ---
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_constraint=True),
        nullable=False,
        default=TaskStatus.NEW,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=TaskPriority.NORMAL.value,
    )

    # --- QA & Gate Data ---
    qa_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="SOP-008 QA evaluation output",
    )
    levi_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Levi gate decision note (approve or return reason)",
    )

    # --- Intelligence Link (Addendum A5) ---
    intel_brief_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="FK to intelligence_briefs — set when task_type=BUILD_FROM_INTEL",
    )

    # --- Container Tracking ---
    container_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        comment="Docker container ID when EXECUTING",
    )
    execution_plane: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="cloud (OpenRouter) or local (Ollama)",
    )

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    executing_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    receipted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Metadata ---
    payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Flexible metadata — varies by task_type",
    )

    # -----------------------------------------------------------------------
    # Constraints — DB-level enforcement, not app-level
    # -----------------------------------------------------------------------

    __table_args__ = (
        # Status CHECK — the state machine boundary at the DB level
        CheckConstraint(
            "status IN ("
            "'NEW','ASSIGNED','EXECUTING','QA_GATE','LEVI_GATE',"
            "'DEPLOYING','COMPLETE','RECEIPTED','FAILED'"
            ")",
            name="valid_status",
        ),
        # Task type CHECK
        CheckConstraint(
            "task_type IN ("
            "'STANDARD','INTELLIGENCE_BRIEF','BUILD_FROM_INTEL',"
            "'OPPORTUNITY','GTM_CAMPAIGN','VOICE_OUTREACH',"
            "'SECURITY_REVIEW','QA_EVALUATION','CHANGE_REQUEST'"
            ")",
            name="valid_task_type",
        ),
        # Priority range
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="valid_priority",
        ),
        # Composite indexes for common query patterns
        Index("ix_tasks_status_priority", "status", "priority"),
        Index("ix_tasks_assigned_status", "assigned_to", "status"),
        Index("ix_tasks_department_status", "department", "status"),
        Index("ix_tasks_created_desc", text("created_at DESC")),
    )

    def __repr__(self) -> str:
        return (
            f"<Task {self.task_ref} "
            f"status={self.status.value} "
            f"type={self.task_type.value}>"
        )
