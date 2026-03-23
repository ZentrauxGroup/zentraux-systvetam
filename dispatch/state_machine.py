"""
SYSTVETAM — Task State Machine
Zentraux Group LLC

This is the ONLY module that may advance task status.
No router, no service, no script touches task.status directly.
The state machine IS the doctrine.

Transition rules from Engineering Directive v1.0:
  NEW → ASSIGNED → EXECUTING → QA_GATE → LEVI_GATE → DEPLOYING → COMPLETE → RECEIPTED
  QA_GATE → EXECUTING   (QA fail-back with correction note)
  LEVI_GATE → ASSIGNED   (Levi return with note)
  Any → FAILED           (terminal — container error, unrecoverable)

DB CHECK constraint is the outer wall. This module is the inner wall.
Both must agree. If they don't, the system stops — not silently proceeds.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.models.task import Task, TaskStatus

logger = logging.getLogger("dispatch.state_machine")


# ---------------------------------------------------------------------------
# Doctrine Violation — surfaces as HTTP 409 via main.py exception handler
# ---------------------------------------------------------------------------

class DoctrineViolation(Exception):
    """
    Raised when any operation violates ZOS doctrine.

    Attributes:
        sop_reference: The SOP that was violated (e.g., "SOP-008", "L0-RECEIPT")
    """

    def __init__(self, message: str, sop_reference: str | None = None):
        self.sop_reference = sop_reference
        super().__init__(message)


# ---------------------------------------------------------------------------
# Legal Transitions — the canonical graph
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.NEW:       [TaskStatus.ASSIGNED, TaskStatus.FAILED],
    TaskStatus.ASSIGNED:  [TaskStatus.EXECUTING, TaskStatus.FAILED],
    TaskStatus.EXECUTING: [TaskStatus.QA_GATE, TaskStatus.FAILED],
    TaskStatus.QA_GATE:   [TaskStatus.LEVI_GATE, TaskStatus.EXECUTING, TaskStatus.FAILED],
    TaskStatus.LEVI_GATE: [TaskStatus.DEPLOYING, TaskStatus.ASSIGNED, TaskStatus.FAILED],
    TaskStatus.DEPLOYING: [TaskStatus.COMPLETE, TaskStatus.FAILED],
    TaskStatus.COMPLETE:  [TaskStatus.RECEIPTED],
    TaskStatus.RECEIPTED: [],
    TaskStatus.FAILED:    [],
}

# Transitions that require a note (fail-back, return, failure)
REQUIRES_NOTE: set[tuple[TaskStatus, TaskStatus]] = {
    (TaskStatus.QA_GATE, TaskStatus.EXECUTING),    # QA fail — why?
    (TaskStatus.LEVI_GATE, TaskStatus.ASSIGNED),    # Levi return — why?
}

# Timestamp fields to set on specific transitions
TIMESTAMP_MAP: dict[TaskStatus, str] = {
    TaskStatus.ASSIGNED:  "assigned_at",
    TaskStatus.EXECUTING: "executing_at",
    TaskStatus.COMPLETE:  "completed_at",
    TaskStatus.RECEIPTED: "receipted_at",
}


# ---------------------------------------------------------------------------
# Core Transition Function
# ---------------------------------------------------------------------------

async def transition_task(
    db: AsyncSession,
    task: Task,
    new_status: TaskStatus,
    actor_id: str,
    note: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Task:
    """
    Advance a task through the state machine.

    This is the ONLY function in the entire codebase that writes
    to task.status. Everything else calls this.

    Args:
        db:         Active async session (caller manages commit).
        task:       The Task ORM instance to advance.
        new_status: Target state.
        actor_id:   Agent ID performing the transition (e.g., "AGT-001").
        note:       Required for fail-back and return transitions.
        payload:    Optional metadata to attach (QA results, etc.).

    Returns:
        The updated Task instance.

    Raises:
        DoctrineViolation: If the transition is illegal or note is missing.
    """
    old_status = task.status

    # --- Guard: terminal states accept nothing ---
    if not VALID_TRANSITIONS.get(old_status):
        raise DoctrineViolation(
            f"Task {task.task_ref} is in terminal state '{old_status.value}'. "
            f"No further transitions permitted.",
            sop_reference="L0-STATE-MACHINE",
        )

    # --- Guard: transition must be in the legal set ---
    if new_status not in VALID_TRANSITIONS[old_status]:
        legal = [s.value for s in VALID_TRANSITIONS[old_status]]
        raise DoctrineViolation(
            f"Illegal transition: {old_status.value} → {new_status.value} "
            f"on task {task.task_ref}. "
            f"Legal targets from {old_status.value}: {legal}",
            sop_reference="L0-STATE-MACHINE",
        )

    # --- Guard: note required for fail-backs and returns ---
    if (old_status, new_status) in REQUIRES_NOTE and not note:
        raise DoctrineViolation(
            f"Transition {old_status.value} → {new_status.value} "
            f"requires a note explaining the reason. "
            f"Task: {task.task_ref}",
            sop_reference="SOP-008" if old_status == TaskStatus.QA_GATE else "L0-GATE",
        )

    # --- Apply transition ---
    task.status = new_status

    # Set timestamp if mapped
    ts_field = TIMESTAMP_MAP.get(new_status)
    if ts_field:
        setattr(task, ts_field, datetime.now(timezone.utc))

    # Store notes on the task
    if note:
        if new_status == TaskStatus.ASSIGNED and old_status == TaskStatus.LEVI_GATE:
            task.levi_note = note
        elif new_status == TaskStatus.EXECUTING and old_status == TaskStatus.QA_GATE:
            task.qa_result = {
                **(task.qa_result or {}),
                "fail_note": note,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }

    # Merge extra payload
    if payload:
        task.payload = {**(task.payload or {}), **payload}

    # Flush to DB so the CHECK constraint validates NOW, not at commit
    db.add(task)
    await db.flush()

    logger.info(
        "TRANSITION %s: %s → %s (actor=%s)",
        task.task_ref,
        old_status.value,
        new_status.value,
        actor_id,
    )

    # --- Publish to Redis ---
    await _publish_transition(task, old_status, new_status, actor_id, note)

    # --- Auto-receipt ---
    await _auto_receipt(db, task, old_status, new_status, actor_id)

    return task


# ---------------------------------------------------------------------------
# Redis publish — fire-and-forget, never blocks transition
# ---------------------------------------------------------------------------

async def _publish_transition(
    task: Task,
    old_status: TaskStatus,
    new_status: TaskStatus,
    actor_id: str,
    note: str | None,
) -> None:
    """Publish state transition event to Redis for Tower Dashboard."""
    try:
        from dispatch.redis_client import publish

        await publish("task_events", {
            "event": "TASK_TRANSITION",
            "task_ref": task.task_ref,
            "task_id": str(task.id),
            "from": old_status.value,
            "to": new_status.value,
            "actor": actor_id,
            "note": note,
            "task_type": task.task_type.value if task.task_type else None,
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
        })
    except Exception as e:
        # Redis failure must NEVER block state transitions
        logger.warning("Redis publish failed for %s transition: %s", task.task_ref, e)


# ---------------------------------------------------------------------------
# Auto-receipt — every transition receipted per L0 doctrine
# ---------------------------------------------------------------------------

async def _auto_receipt(
    db: AsyncSession,
    task: Task,
    old_status: TaskStatus,
    new_status: TaskStatus,
    actor_id: str,
) -> None:
    """Generate a receipt for every state transition. L0 doctrine: no exceptions."""
    try:
        from dispatch.receipt_engine import generate_receipt

        receipt_type = _receipt_type_for_transition(old_status, new_status)
        await generate_receipt(
            db=db,
            receipt_type=receipt_type,
            task=task,
            actor_id=actor_id,
        )
    except Exception as e:
        # Receipt failure is logged but does NOT block the transition.
        # The receipt gap will be caught by the compliance audit query.
        logger.error(
            "RECEIPT GENERATION FAILED for %s (%s → %s): %s",
            task.task_ref, old_status.value, new_status.value, e,
        )


def _receipt_type_for_transition(
    old_status: TaskStatus,
    new_status: TaskStatus,
) -> str:
    """Map a state transition to its receipt type."""
    mapping = {
        (TaskStatus.NEW, TaskStatus.ASSIGNED):        "TASK_ASSIGNED",
        (TaskStatus.ASSIGNED, TaskStatus.EXECUTING):   "CREW_ACTIVATED",
        (TaskStatus.EXECUTING, TaskStatus.QA_GATE):    "QA_EVALUATION",
        (TaskStatus.QA_GATE, TaskStatus.LEVI_GATE):    "QA_PASSED",
        (TaskStatus.QA_GATE, TaskStatus.EXECUTING):    "QA_FAILED",
        (TaskStatus.LEVI_GATE, TaskStatus.DEPLOYING):  "GATE_APPROVED",
        (TaskStatus.LEVI_GATE, TaskStatus.ASSIGNED):   "GATE_RETURNED",
        (TaskStatus.DEPLOYING, TaskStatus.COMPLETE):   "TASK_COMPLETE",
        (TaskStatus.COMPLETE, TaskStatus.RECEIPTED):   "TASK_RECEIPTED",
    }

    result = mapping.get((old_status, new_status))
    if result:
        return result

    if new_status == TaskStatus.FAILED:
        return "ERROR_LOGGED"

    return "SYSTEM_EVENT"


# ---------------------------------------------------------------------------
# Query helpers — used by routers to load tasks before transitioning
# ---------------------------------------------------------------------------

async def get_task_by_id(db: AsyncSession, task_id: str) -> Task:
    """Load a task by UUID. Raises DoctrineViolation if not found."""
    import uuid as _uuid

    try:
        parsed_id = _uuid.UUID(task_id)
    except ValueError:
        raise DoctrineViolation(
            f"Invalid task ID format: {task_id}",
            sop_reference="L0-STATE-MACHINE",
        )

    result = await db.execute(select(Task).where(Task.id == parsed_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise DoctrineViolation(
            f"Task not found: {task_id}",
            sop_reference="L0-STATE-MACHINE",
        )

    return task


async def get_task_by_ref(db: AsyncSession, task_ref: str) -> Task:
    """Load a task by human-readable ref (ZG-NNNN). Raises DoctrineViolation if not found."""
    result = await db.execute(select(Task).where(Task.task_ref == task_ref))
    task = result.scalar_one_or_none()

    if task is None:
        raise DoctrineViolation(
            f"Task not found: {task_ref}",
            sop_reference="L0-STATE-MACHINE",
        )

    return task
