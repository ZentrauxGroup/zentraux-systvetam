"""
SYSTVETAM — Receipt Model
Zentraux Group LLC

Receipts are immutable. Append-only. No updates. No deletes.
This is L0 doctrine — SOP-RECEIPT-001.

DB enforcement: PostgreSQL trigger prevents UPDATE and DELETE.
Application enforcement: No update/delete methods exist on this model.
Belt and suspenders. The receipt is the proof.

Receipt types from Engineering Directive v1.0:
  TASK_COMPLETE, GATE_APPROVED, GATE_RETURNED, TASK_CREATED,
  TASK_ASSIGNED, CREW_ACTIVATED, CREW_DEACTIVATED, SYSTEM_EVENT,
  ERROR_LOGGED, CHANGE_REQUEST, VENDOR_ONBOARD, FINANCIAL_APPROVAL,
  QA_EVALUATION, QA_PASSED, QA_FAILED, TASK_RECEIPTED
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dispatch.database import Base


class ReceiptType(str, enum.Enum):
    """All receipt types from the directive + state machine transitions."""
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_RECEIPTED = "TASK_RECEIPTED"
    GATE_APPROVED = "GATE_APPROVED"
    GATE_RETURNED = "GATE_RETURNED"
    CREW_ACTIVATED = "CREW_ACTIVATED"
    CREW_DEACTIVATED = "CREW_DEACTIVATED"
    QA_EVALUATION = "QA_EVALUATION"
    QA_PASSED = "QA_PASSED"
    QA_FAILED = "QA_FAILED"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    ERROR_LOGGED = "ERROR_LOGGED"
    CHANGE_REQUEST = "CHANGE_REQUEST"
    VENDOR_ONBOARD = "VENDOR_ONBOARD"
    FINANCIAL_APPROVAL = "FINANCIAL_APPROVAL"


class Receipt(Base):
    __tablename__ = "receipts"

    # --- Identity ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    receipt_ref: Mapped[str] = mapped_column(
        String(60),
        unique=True,
        nullable=False,
        index=True,
        comment="Human-readable ref: RCPT-{task_ref}-{STATUS}-{timestamp}",
    )

    # --- Classification ---
    receipt_type: Mapped[ReceiptType] = mapped_column(
        Enum(ReceiptType, name="receipt_type", create_constraint=True),
        nullable=False,
    )
    sop_reference: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="SOP that triggered this receipt (e.g., SOP-008)",
    )

    # --- Links ---
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    crew_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Content ---
    issued_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Actor ID — SYSTEM for auto-receipts, AGT-001 for Levi manual",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description of what happened",
    )
    payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Structured metadata — varies by receipt_type",
    )

    # --- Timestamp (single — receipts are born once, never modified) ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # -----------------------------------------------------------------------
    # Indexes
    # -----------------------------------------------------------------------

    __table_args__ = (
        Index("ix_receipts_type_created", "receipt_type", text("created_at DESC")),
        Index("ix_receipts_task_id", "task_id"),
        Index("ix_receipts_created_desc", text("created_at DESC")),
    )

    def __repr__(self) -> str:
        return (
            f"<Receipt {self.receipt_ref} "
            f"type={self.receipt_type.value}>"
        )
