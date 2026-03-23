"""
SYSTVETAM — Receipt Engine
Zentraux Group LLC

Called automatically on every state transition by state_machine.py.
No manual receipt creation exists in the system.
Every action produces a receipt. This is L0 doctrine.

Receipt ID format:  RCPT-{task_ref}-{RECEIPT_TYPE}-{YYYYMMDD}-{seq}
Example:            RCPT-ZG-0042-TASK_COMPLETE-20260321-001

Append-only: This module only INSERTs. No UPDATE. No DELETE.
DB trigger (SOP-RECEIPT-001) is the enforcement backstop.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.models.receipt import Receipt, ReceiptType
from dispatch.models.task import Task

logger = logging.getLogger("dispatch.receipt_engine")

# SOP mapping — which SOP governs each receipt type
SOP_MAP: dict[str, str] = {
    "TASK_CREATED":       "SOP-TASK-001",
    "TASK_ASSIGNED":      "SOP-TASK-001",
    "TASK_COMPLETE":      "SOP-TASK-001",
    "TASK_RECEIPTED":     "L0-RECEIPT",
    "GATE_APPROVED":      "L0-GATE",
    "GATE_RETURNED":      "L0-GATE",
    "CREW_ACTIVATED":     "SOP-CREW-001",
    "CREW_DEACTIVATED":   "SOP-CREW-001",
    "QA_EVALUATION":      "SOP-008",
    "QA_PASSED":          "SOP-008",
    "QA_FAILED":          "SOP-008",
    "SYSTEM_EVENT":       "L0-SYSTEM",
    "ERROR_LOGGED":       "L0-SYSTEM",
    "CHANGE_REQUEST":     "SOP-CR-001",
    "VENDOR_ONBOARD":     "SOP-VENDOR-001",
    "FINANCIAL_APPROVAL": "SOP-FIN-001",
}


# ---------------------------------------------------------------------------
# Receipt Reference Generator
# ---------------------------------------------------------------------------

async def _generate_receipt_ref(
    db: AsyncSession,
    task: Task | None,
    receipt_type: str,
) -> str:
    """
    Generate a unique receipt reference.
    Format: RCPT-{task_ref}-{TYPE}-{YYYYMMDD}-{NNN}

    If no task is linked (system events), uses RCPT-SYS-{TYPE}-{YYYYMMDD}-{NNN}.
    Sequence number is derived from today's receipt count to avoid collisions.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")

    if task:
        prefix = f"RCPT-{task.task_ref}-{receipt_type}-{date_str}"
    else:
        prefix = f"RCPT-SYS-{receipt_type}-{date_str}"

    # Count existing receipts with this prefix today for sequence
    count_result = await db.execute(
        select(func.count()).where(Receipt.receipt_ref.like(f"{prefix}%"))
    )
    seq = (count_result.scalar() or 0) + 1

    return f"{prefix}-{seq:03d}"


# ---------------------------------------------------------------------------
# Summary Builder
# ---------------------------------------------------------------------------

def _build_summary(
    receipt_type: str,
    task: Task | None,
    actor_id: str,
) -> str:
    """Build a human-readable summary for the receipt."""
    task_label = f"Task {task.task_ref}" if task else "System"
    assigned_label = f" (crew: {task.assigned_to})" if task and task.assigned_to else ""

    summaries = {
        "TASK_CREATED":       f"{task_label} created by {actor_id}.",
        "TASK_ASSIGNED":      f"{task_label} assigned{assigned_label} by {actor_id}.",
        "CREW_ACTIVATED":     f"{task_label} execution started{assigned_label}.",
        "QA_EVALUATION":      f"{task_label} submitted to QA gate.",
        "QA_PASSED":          f"{task_label} passed QA gate. Advancing to Levi gate.",
        "QA_FAILED":          f"{task_label} failed QA gate. Returned to EXECUTING.",
        "GATE_APPROVED":      f"{task_label} approved by {actor_id} at Levi gate.",
        "GATE_RETURNED":      f"{task_label} returned by {actor_id} at Levi gate.",
        "TASK_COMPLETE":      f"{task_label} deployment complete.",
        "TASK_RECEIPTED":     f"{task_label} fully receipted. Lifecycle closed.",
        "CREW_DEACTIVATED":   f"Crew member deactivated by {actor_id}.",
        "ERROR_LOGGED":       f"{task_label} entered FAILED state. Requires investigation.",
        "SYSTEM_EVENT":       f"System event recorded by {actor_id}.",
        "CHANGE_REQUEST":     f"Change request filed by {actor_id}.",
        "VENDOR_ONBOARD":     f"Vendor onboarded by {actor_id}.",
        "FINANCIAL_APPROVAL": f"Financial approval recorded by {actor_id}.",
    }

    return summaries.get(receipt_type, f"{receipt_type} recorded for {task_label}.")


# ---------------------------------------------------------------------------
# Core Receipt Generator
# ---------------------------------------------------------------------------

async def generate_receipt(
    db: AsyncSession,
    receipt_type: str,
    task: Task | None = None,
    crew_member_id: str | None = None,
    actor_id: str = "SYSTEM",
    payload: dict[str, Any] | None = None,
) -> Receipt:
    """
    Generate and persist an immutable receipt record.

    Called by state_machine.py on every transition.
    Can also be called directly for non-task events (system, crew, vendor).

    This function only INSERTs. It never updates or deletes.
    The DB trigger on the receipts table is the enforcement backstop.

    Args:
        db:              Active async session.
        receipt_type:    One of the ReceiptType enum values (as string).
        task:            The related Task, if any.
        crew_member_id:  UUID string of crew member, if applicable.
        actor_id:        Who triggered this (agent ID or "SYSTEM").
        payload:         Extra structured data to attach.

    Returns:
        The created Receipt ORM instance (already flushed, not yet committed).
    """
    import uuid as _uuid

    # Resolve receipt type enum
    try:
        resolved_type = ReceiptType(receipt_type)
    except ValueError:
        logger.warning(
            "Unknown receipt type '%s' — defaulting to SYSTEM_EVENT", receipt_type
        )
        resolved_type = ReceiptType.SYSTEM_EVENT

    # Generate unique ref
    receipt_ref = await _generate_receipt_ref(db, task, receipt_type)

    # Parse crew member ID if provided
    parsed_crew_id = None
    if crew_member_id:
        try:
            parsed_crew_id = _uuid.UUID(crew_member_id)
        except ValueError:
            pass

    # If task has an assigned crew member and none was explicitly passed, use it
    if parsed_crew_id is None and task and task.assigned_to:
        parsed_crew_id = task.assigned_to

    # Build the receipt
    receipt = Receipt(
        receipt_ref=receipt_ref,
        receipt_type=resolved_type,
        task_id=task.id if task else None,
        crew_member_id=parsed_crew_id,
        issued_by=actor_id,
        summary=_build_summary(receipt_type, task, actor_id),
        payload=payload or {},
        sop_reference=SOP_MAP.get(receipt_type),
    )

    db.add(receipt)
    await db.flush()

    logger.info("RECEIPT %s: %s (task=%s)", receipt_ref, receipt_type,
                task.task_ref if task else "N/A")

    # Publish to Redis — fire and forget
    await _publish_receipt(receipt, task)

    return receipt


# ---------------------------------------------------------------------------
# Redis publish — Tower Dashboard receipt feed
# ---------------------------------------------------------------------------

async def _publish_receipt(receipt: Receipt, task: Task | None) -> None:
    """Publish receipt event to Redis for live Tower Dashboard feed."""
    try:
        from dispatch.redis_client import publish

        await publish("receipts", {
            "event": "RECEIPT_FILED",
            "receipt_ref": receipt.receipt_ref,
            "receipt_type": receipt.receipt_type.value,
            "task_ref": task.task_ref if task else None,
            "summary": receipt.summary,
            "sop_reference": receipt.sop_reference,
        })
    except Exception as e:
        logger.warning("Redis publish failed for receipt %s: %s", receipt.receipt_ref, e)
