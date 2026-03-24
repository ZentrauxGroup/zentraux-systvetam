"""
SYSTVETAM — Crew Router
Zentraux Group LLC

The 16-member crew roster. Each crew member is a living entity in the system —
trackable by status, assignable to tasks, visible in the Tower Dashboard
as a pulsing avatar with real-time presence.

Endpoints from Engineering Directive v1.0:
  GET  /crew                  All crew with live status (filter: status, department)
  GET  /crew/{callsign}       Single crew member + active tasks
  GET  /crew/{callsign}/tasks Task history for crew member, paginated
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.database import get_db
from dispatch.models.crew_member import CrewMember, CrewStatus
from dispatch.models.task import Task, TaskStatus
from dispatch.schemas.crew import (
    CrewListResponse,
    CrewMemberDetailResponse,
    CrewMemberResponse,
)
from dispatch.schemas.task import TaskListResponse, TaskResponse
from dispatch.state_machine import DoctrineViolation
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import Header
from dispatch.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /crew — Full roster with live status
# ---------------------------------------------------------------------------

@router.get("", response_model=CrewListResponse)
async def list_crew(
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter: ACTIVE, IDLE, EXECUTING, ERROR, OFFLINE"),
    department: str | None = Query(None, description="Filter by department"),
):
    """
    List all crew members with live status.
    This is the data behind the Tower Dashboard crew roster grid.
    """
    query = select(CrewMember)

    if status:
        try:
            resolved = CrewStatus(status)
            query = query.where(CrewMember.status == resolved)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid crew status filter: {status}. "
                f"Valid: {[s.value for s in CrewStatus]}",
                sop_reference="SOP-CREW-001",
            )

    if department:
        query = query.where(CrewMember.department == department)

    query = query.order_by(CrewMember.department.asc(), CrewMember.callsign.asc())

    result = await db.execute(query)
    crew = result.scalars().all()

    # Counts for dashboard summary
    active_count = sum(1 for c in crew if c.status in (CrewStatus.ACTIVE, CrewStatus.IDLE))
    executing_count = sum(1 for c in crew if c.status == CrewStatus.EXECUTING)

    return CrewListResponse(
        crew=[CrewMemberResponse.model_validate(c) for c in crew],
        total=len(crew),
        active_count=active_count,
        executing_count=executing_count,
    )


# ---------------------------------------------------------------------------
# GET /crew/{callsign} — Single crew member detail
# ---------------------------------------------------------------------------

@router.get("/{callsign}", response_model=CrewMemberDetailResponse)
async def get_crew_member(
    callsign: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Single crew member detail with active tasks.
    Callsign is lowercase hyphenated: jordan-reese, marcus-reed, etc.
    """
    result = await db.execute(
        select(CrewMember).where(CrewMember.callsign == callsign.lower())
    )
    member = result.scalar_one_or_none()

    if member is None:
        raise DoctrineViolation(
            f"Crew member not found: {callsign}",
            sop_reference="SOP-CREW-001",
        )

    # Load active tasks (not RECEIPTED or FAILED)
    active_statuses = [
        TaskStatus.NEW, TaskStatus.ASSIGNED, TaskStatus.EXECUTING,
        TaskStatus.QA_GATE, TaskStatus.LEVI_GATE, TaskStatus.DEPLOYING,
        TaskStatus.COMPLETE,
    ]
    tasks_result = await db.execute(
        select(Task)
        .where(Task.assigned_to == member.id)
        .where(Task.status.in_(active_statuses))
        .order_by(Task.priority.asc(), Task.created_at.desc())
    )
    active_tasks = tasks_result.scalars().all()

    response = CrewMemberDetailResponse.model_validate(member)
    response.active_tasks = [TaskResponse.model_validate(t) for t in active_tasks]

    return response


# ---------------------------------------------------------------------------
# GET /crew/{callsign}/tasks — Task history
# ---------------------------------------------------------------------------

@router.get("/{callsign}/tasks", response_model=TaskListResponse)
async def get_crew_tasks(
    callsign: str,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by task status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Full task history for a crew member. Paginated, newest first.
    Includes completed and receipted tasks — the full trail.
    """
    # Resolve crew member
    member_result = await db.execute(
        select(CrewMember).where(CrewMember.callsign == callsign.lower())
    )
    member = member_result.scalar_one_or_none()

    if member is None:
        raise DoctrineViolation(
            f"Crew member not found: {callsign}",
            sop_reference="SOP-CREW-001",
        )

    # Build task query
    query = select(Task).where(Task.assigned_to == member.id)

    if status:
        try:
            resolved = TaskStatus(status)
            query = query.where(Task.status == resolved)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid task status filter: {status}",
                sop_reference="L0-STATE-MACHINE",
            )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order and paginate
    query = query.order_by(Task.created_at.desc())
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
# PATCH/Sprint 5: Crew Heartbeat Status Endpoint
# Receives heartbeat from agent-mesh every 30s — updates status + last_heartbeat
# Integration: agent-mesh/heartbeat.py → PATCH /crew/{callsign}/status → DB
# ---------------------------------------------------------------------------

class HeartbeatRequest(BaseModel):
    """
    Heartbeat payload from agent-mesh.
    Updates crew member status and last_seen timestamp.
    """
    status: str  # "ACTIVE", "STANDBY", "OFFLINE", "EXECUTING"
    last_seen: datetime


class HeartbeatResponse(BaseModel):
    """Response confirming heartbeat was received and applied."""
    callsign: str
    status: str
    last_heartbeat: datetime
    acknowledged: bool = True


# --- Add this endpoint to the existing router ---

# ---------------------------------------------------------------------------
# PATCH /crew/{callsign}/status — Agent-Mesh Heartbeat Receiver
# ---------------------------------------------------------------------------

@router.patch("/{callsign}/status", response_model=HeartbeatResponse)
async def update_crew_status(
    callsign: str,
    payload: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None),
):
    """
    Heartbeat endpoint for agent-mesh service.
    Called every 30 seconds per crew session.
    This is what turns the Tower Lobby dots gold.

    Auth: Bearer token from MESH_SERVICE_TOKEN.
    Lookup: case-insensitive callsign match to handle both
    canonical callsigns (FORGE, CLOSE) and legacy seed data
    (marcus-reed, jordan-reese).

    Status mapping from agent-mesh → Dispatch CrewStatus:
      ACTIVE    → ACTIVE
      STANDBY   → IDLE
      EXECUTING → EXECUTING
      OFFLINE   → OFFLINE
    """
    # --- Auth: validate mesh service token ---
    # In production, MESH_SERVICE_TOKEN is a JWT issued by Dispatch.
    # For Sprint 5 initial integration, we accept Bearer token match.
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        mesh_token = getattr(settings, "MESH_SERVICE_TOKEN", None) or getattr(
            settings, "mesh_service_token", ""
        )
        if mesh_token and token != mesh_token:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=401,
                detail="Invalid mesh service token",
            )

    # --- Lookup crew member (case-insensitive) ---
    # Agent-mesh sends canonical callsigns: FORGE, CLOSE, NOVA
    # DB may have lowercase-hyphenated: marcus-reed, jordan-reese
    # Try both patterns until seed data is refreshed.
    result = await db.execute(
        select(CrewMember).where(
            func.upper(CrewMember.callsign) == callsign.upper()
        )
    )
    member = result.scalar_one_or_none()

    if member is None:
        # Not found — return 404 (heartbeat service logs this and continues)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404,
            content={
                "error": "CREW_NOT_FOUND",
                "detail": f"No crew member with callsign: {callsign}",
                "callsign": callsign,
            },
        )

    # --- Map mesh status → Dispatch CrewStatus ---
    status_map = {
        "ACTIVE": CrewStatus.ACTIVE,
        "STANDBY": CrewStatus.IDLE,
        "EXECUTING": CrewStatus.EXECUTING,
        "OFFLINE": CrewStatus.OFFLINE,
        # Fallbacks for direct enum matches
        "IDLE": CrewStatus.IDLE,
        "ERROR": CrewStatus.ERROR,
    }

    new_status = status_map.get(payload.status.upper())
    if new_status is None:
        # Unknown status — default to ACTIVE rather than rejecting
        # The heartbeat should never fail on a valid crew member
        new_status = CrewStatus.ACTIVE

    # --- Update DB ---
    member.status = new_status
    member.last_heartbeat = payload.last_seen
    await db.commit()
    await db.refresh(member)

    return HeartbeatResponse(
        callsign=member.callsign,
        status=member.status.value,
        last_heartbeat=member.last_heartbeat,
        acknowledged=True,
    )
