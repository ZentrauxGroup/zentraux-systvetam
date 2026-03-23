"""
SYSTVETAM — Gates Router
Zentraux Group LLC

The gate queue is where the Architect exercises judgment.
QA_GATE: automated quality check. LEVI_GATE: human approval.
Gold ring appears in Tower Dashboard. Levi decides. The system moves.

Every gate decision goes through state_machine.transition_task().
No gate endpoint writes task.status directly.

Endpoints from Engineering Directive v1.0:
  GET   /gates/pending          All tasks awaiting gate decision
  POST  /gates/{id}/approve     Approve → advance task
  POST  /gates/{id}/return      Return → regress task with note
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.database import get_db
from dispatch.models.task import Task, TaskStatus
from dispatch.schemas.task import (
    GateActionRequest,
    TaskListResponse,
    TaskResponse,
)
from dispatch.state_machine import (
    DoctrineViolation,
    get_task_by_id,
    transition_task,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Gate type → next status mapping
# ---------------------------------------------------------------------------

GATE_APPROVE_MAP: dict[TaskStatus, TaskStatus] = {
    TaskStatus.QA_GATE: TaskStatus.LEVI_GATE,
    TaskStatus.LEVI_GATE: TaskStatus.DEPLOYING,
}

GATE_RETURN_MAP: dict[TaskStatus, TaskStatus] = {
    TaskStatus.QA_GATE: TaskStatus.EXECUTING,
    TaskStatus.LEVI_GATE: TaskStatus.ASSIGNED,
}

GATE_STATUSES = [TaskStatus.QA_GATE, TaskStatus.LEVI_GATE]


# ---------------------------------------------------------------------------
# GET /gates/pending — Levi's queue
# ---------------------------------------------------------------------------

@router.get("/pending", response_model=TaskListResponse)
async def list_pending_gates(
    db: AsyncSession = Depends(get_db),
    gate_type: str | None = Query(
        None,
        description="Filter: QA_GATE or LEVI_GATE. Omit for both.",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List all tasks currently awaiting gate decisions.
    Ordered by priority ASC (critical first), then created_at ASC (oldest first).
    This is the gold-ring queue in Tower Dashboard.
    """
    query = select(Task)

    if gate_type:
        try:
            resolved = TaskStatus(gate_type)
            if resolved not in GATE_STATUSES:
                raise ValueError
            query = query.where(Task.status == resolved)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid gate_type filter: {gate_type}. Use QA_GATE or LEVI_GATE.",
                sop_reference="L0-GATE",
            )
    else:
        query = query.where(Task.status.in_(GATE_STATUSES))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Priority first, oldest first within priority (FIFO within tier)
    query = query.order_by(Task.priority.asc(), Task.created_at.asc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# POST /gates/{id}/approve — Advance gate
# ---------------------------------------------------------------------------

@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_gate(
    task_id: str,
    body: GateActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a gate. Advances task to the next state:
      QA_GATE   → LEVI_GATE
      LEVI_GATE → DEPLOYING
    """
    task = await get_task_by_id(db, task_id)

    next_status = GATE_APPROVE_MAP.get(task.status)
    if next_status is None:
        raise DoctrineViolation(
            f"Task {task.task_ref} is in state {task.status.value}, "
            f"which is not a gate state. Cannot approve.",
            sop_reference="L0-GATE",
        )

    task = await transition_task(
        db=db,
        task=task,
        new_status=next_status,
        actor_id=body.actor_id,
        note=body.note,
    )
    return task


# ---------------------------------------------------------------------------
# POST /gates/{id}/return — Return with note
# ---------------------------------------------------------------------------

@router.post("/{task_id}/return", response_model=TaskResponse)
async def return_gate(
    task_id: str,
    body: GateActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Return a gate. Regresses task to correction state:
      QA_GATE   → EXECUTING  (note required by state machine)
      LEVI_GATE → ASSIGNED   (note required by state machine)
    """
    task = await get_task_by_id(db, task_id)

    return_status = GATE_RETURN_MAP.get(task.status)
    if return_status is None:
        raise DoctrineViolation(
            f"Task {task.task_ref} is in state {task.status.value}, "
            f"which is not a gate state. Cannot return.",
            sop_reference="L0-GATE",
        )

    if not body.note:
        raise DoctrineViolation(
            f"Gate return on {task.task_ref} requires a note explaining "
            f"why the task is being sent back.",
            sop_reference="L0-GATE",
        )

    task = await transition_task(
        db=db,
        task=task,
        new_status=return_status,
        actor_id=body.actor_id,
        note=body.note,
    )
    return task
