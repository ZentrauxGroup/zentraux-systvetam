"""
SYSTVETAM — Tasks Router
Zentraux Group LLC

Task CRUD and state transition endpoints.
Every state change goes through state_machine.transition_task().
No endpoint writes task.status directly. The machine IS the doctrine.

Endpoints from Engineering Directive v1.0:
  POST   /tasks                 Create task (state: NEW)
  GET    /tasks                 List (filter: status, department, assigned_to)
  GET    /tasks/{id}            Detail by UUID or ZG-ref
  PATCH  /tasks/{id}/assign     NEW → ASSIGNED
  PATCH  /tasks/{id}/execute    ASSIGNED → EXECUTING
  PATCH  /tasks/{id}/submit     EXECUTING → QA_GATE
  PATCH  /tasks/{id}/qa-pass    QA_GATE → LEVI_GATE
  PATCH  /tasks/{id}/qa-fail    QA_GATE → EXECUTING (note required)
  PATCH  /tasks/{id}/approve    LEVI_GATE → DEPLOYING
  PATCH  /tasks/{id}/return     LEVI_GATE → ASSIGNED (note required)
"""

import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.database import get_db
from dispatch.models.task import Task, TaskStatus, TaskType
from dispatch.receipt_engine import generate_receipt
from dispatch.schemas.task import (
    ApproveRequest,
    AssignRequest,
    ExecuteRequest,
    QAFailRequest,
    QAPassRequest,
    ReturnRequest,
    SubmitRequest,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
)
from dispatch.state_machine import (
    DoctrineViolation,
    get_task_by_id,
    get_task_by_ref,
    transition_task,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_task_ref() -> str:
    """
    Generate a human-readable task reference: ZG-NNNN.
    Uses timestamp-based sequence for uniqueness without DB round-trip.
    """
    now = datetime.now(timezone.utc)
    seq = int(now.timestamp() * 1000) % 99999
    return f"ZG-{seq:05d}"


async def _resolve_task(db: AsyncSession, task_id: str) -> Task:
    """
    Resolve a task by either UUID or ZG-ref.
    Accepts both formats so callers can use whichever they have.
    """
    if task_id.upper().startswith("ZG-"):
        return await get_task_by_ref(db, task_id.upper())
    return await get_task_by_id(db, task_id)


# ---------------------------------------------------------------------------
# POST /tasks — Create
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new task in state NEW.
    Auto-generates task_ref and fires a TASK_CREATED receipt.
    """
    # Validate task_type
    try:
        resolved_type = TaskType(body.task_type)
    except ValueError:
        raise DoctrineViolation(
            f"Invalid task_type: {body.task_type}. "
            f"Valid types: {[t.value for t in TaskType]}",
            sop_reference="L0-STATE-MACHINE",
        )

    task = Task(
        task_ref=_generate_task_ref(),
        title=body.title,
        description=body.description,
        task_type=resolved_type,
        department=body.department,
        source=body.source,
        requested_by=body.requested_by,
        status=TaskStatus.NEW,
        priority=body.priority,
        intel_brief_id=body.intel_brief_id,
        payload=body.payload or {},
    )

    db.add(task)
    await db.flush()

    # Auto-receipt: TASK_CREATED (L0 doctrine — every action receipted)
    await generate_receipt(
        db=db,
        receipt_type="TASK_CREATED",
        task=task,
        actor_id=body.requested_by,
    )

    return task


# ---------------------------------------------------------------------------
# GET /tasks — List
# ---------------------------------------------------------------------------

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by status enum value"),
    department: str | None = Query(None, description="Filter by department"),
    assigned_to: _uuid.UUID | None = Query(None, description="Filter by crew member UUID"),
    task_type: str | None = Query(None, description="Filter by task_type enum value"),
    priority: int | None = Query(None, ge=1, le=5),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List tasks with optional filters. Ordered by priority ASC, created_at DESC."""
    query = select(Task)

    if status:
        try:
            resolved_status = TaskStatus(status)
            query = query.where(Task.status == resolved_status)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid status filter: {status}",
                sop_reference="L0-STATE-MACHINE",
            )

    if department:
        query = query.where(Task.department == department)

    if assigned_to:
        query = query.where(Task.assigned_to == assigned_to)

    if task_type:
        try:
            resolved_type = TaskType(task_type)
            query = query.where(Task.task_type == resolved_type)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid task_type filter: {task_type}",
                sop_reference="L0-STATE-MACHINE",
            )

    if priority is not None:
        query = query.where(Task.priority == priority)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Task.priority.asc(), Task.created_at.desc())
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
# GET /tasks/{id} — Detail
# ---------------------------------------------------------------------------

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single task by UUID or ZG-ref."""
    task = await _resolve_task(db, task_id)
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/assign — NEW → ASSIGNED
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: str,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
):
    """Assign a task to a crew member. Transitions NEW → ASSIGNED."""
    task = await _resolve_task(db, task_id)
    task.assigned_to = body.assigned_to
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.ASSIGNED,
        actor_id=body.actor_id,
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/execute — ASSIGNED → EXECUTING
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/execute", response_model=TaskResponse)
async def execute_task(
    task_id: str,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Begin task execution. Transitions ASSIGNED → EXECUTING."""
    task = await _resolve_task(db, task_id)
    task.execution_plane = body.execution_plane
    if body.container_id:
        task.container_id = body.container_id
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.EXECUTING,
        actor_id=body.actor_id,
        payload={"execution_plane": body.execution_plane},
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/submit — EXECUTING → QA_GATE
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/submit", response_model=TaskResponse)
async def submit_task(
    task_id: str,
    body: SubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit task output for QA evaluation. Transitions EXECUTING → QA_GATE."""
    task = await _resolve_task(db, task_id)
    if body.output:
        task.output = body.output
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.QA_GATE,
        actor_id=body.actor_id,
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/qa-pass — QA_GATE → LEVI_GATE
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/qa-pass", response_model=TaskResponse)
async def qa_pass_task(
    task_id: str,
    body: QAPassRequest,
    db: AsyncSession = Depends(get_db),
):
    """QA passed. Advances QA_GATE → LEVI_GATE."""
    task = await _resolve_task(db, task_id)
    if body.qa_result:
        task.qa_result = {**(task.qa_result or {}), **body.qa_result, "passed": True}
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.LEVI_GATE,
        actor_id=body.actor_id,
        payload={"qa_passed": True},
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/qa-fail — QA_GATE → EXECUTING (note required)
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/qa-fail", response_model=TaskResponse)
async def qa_fail_task(
    task_id: str,
    body: QAFailRequest,
    db: AsyncSession = Depends(get_db),
):
    """QA failed. Returns QA_GATE → EXECUTING with correction note."""
    task = await _resolve_task(db, task_id)
    if body.qa_result:
        task.qa_result = {**(task.qa_result or {}), **body.qa_result, "passed": False}
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.EXECUTING,
        actor_id=body.actor_id,
        note=body.note,
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/approve — LEVI_GATE → DEPLOYING
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/approve", response_model=TaskResponse)
async def approve_task(
    task_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Levi approves. Advances LEVI_GATE → DEPLOYING."""
    task = await _resolve_task(db, task_id)
    if body.note:
        task.levi_note = body.note
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.DEPLOYING,
        actor_id=body.actor_id,
    )
    return task


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}/return — LEVI_GATE → ASSIGNED (note required)
# ---------------------------------------------------------------------------

@router.patch("/{task_id}/return", response_model=TaskResponse)
async def return_task(
    task_id: str,
    body: ReturnRequest,
    db: AsyncSession = Depends(get_db),
):
    """Levi returns task. Regresses LEVI_GATE → ASSIGNED with note."""
    task = await _resolve_task(db, task_id)
    task = await transition_task(
        db=db,
        task=task,
        new_status=TaskStatus.ASSIGNED,
        actor_id=body.actor_id,
        note=body.note,
    )
    return task
