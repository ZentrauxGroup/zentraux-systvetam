"""
main.py — SYSTVETAM Agent Mesh Service
Zentraux Group LLC | Sprint 5

Single Railway service. 16 agent sessions. All receipted.

Startup sequence:
  1. SessionRegistry.initialize() — 16 AgentSession instances loaded
  2. TaskExecutor.start() — Redis + HTTP connections for result delivery
  3. TaskRouter.start() — Redis subscriber on dept:*, routes to sessions
  4. HeartbeatService.start() — 30s loop pinging Dispatch for all 16

Shutdown sequence (reverse order):
  1. HeartbeatService.stop()
  2. TaskRouter.stop()
  3. TaskExecutor.stop()
  4. SessionRegistry.shutdown()
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from mesh.config import get_settings
from mesh.executor import TaskExecutor
from mesh.heartbeat import HeartbeatService
from mesh.models import HealthResponse, MeshError, MeshStatus
from mesh.registry import SessionRegistry
from mesh.router import TaskRouter

logger = structlog.get_logger("agent-mesh")

# --- Singletons (lifespan-managed) ---
_registry = SessionRegistry()
_executor = TaskExecutor()
_router = TaskRouter()
_heartbeat = HeartbeatService()
_boot_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Full boot and shutdown sequence.
    Order matters. Each step depends on the one before it.
    """
    global _boot_time
    _boot_time = time.monotonic()

    settings = get_settings()
    logger.info(
        "agent-mesh.startup.begin",
        zos_env=settings.zos_env,
        dispatch_url=settings.dispatch_url,
        default_model=settings.default_model,
        opus_callsigns=list(settings.opus_callsigns),
    )

    # --- STARTUP SEQUENCE ---

    # 1. Initialize all 16 agent sessions (load role files, open HTTP pool)
    try:
        await _registry.initialize()
        logger.info(
            "agent-mesh.startup.registry",
            sessions=_registry.session_count,
        )
    except Exception as e:
        logger.error("agent-mesh.startup.registry_failed", error=str(e))
        raise

    # 2. Start executor (Redis + HTTP for result delivery)
    try:
        await _executor.start()
        logger.info("agent-mesh.startup.executor")
    except Exception as e:
        logger.error("agent-mesh.startup.executor_failed", error=str(e))
        await _registry.shutdown()
        raise

    # 3. Start router (Redis subscriber on dept:*)
    try:
        await _router.start(registry=_registry, executor=_executor)
        logger.info("agent-mesh.startup.router")
    except Exception as e:
        logger.error("agent-mesh.startup.router_failed", error=str(e))
        await _executor.stop()
        await _registry.shutdown()
        raise

    # 4. Start heartbeat (30s loop → Dispatch)
    try:
        await _heartbeat.start(registry=_registry)
        logger.info("agent-mesh.startup.heartbeat")
    except Exception as e:
        logger.error("agent-mesh.startup.heartbeat_failed", error=str(e))
        await _router.stop()
        await _executor.stop()
        await _registry.shutdown()
        raise

    elapsed = round(time.monotonic() - _boot_time, 2)
    logger.info(
        "agent-mesh.startup.complete",
        sessions=_registry.session_count,
        elapsed_s=elapsed,
        message=f"{_registry.session_count} sessions ready — mesh is breathing",
    )

    yield

    # --- SHUTDOWN SEQUENCE (reverse order) ---
    logger.info("agent-mesh.shutdown.begin")

    await _heartbeat.stop()
    logger.info("agent-mesh.shutdown.heartbeat")

    await _router.stop()
    logger.info("agent-mesh.shutdown.router")

    await _executor.stop()
    logger.info("agent-mesh.shutdown.executor")

    await _registry.shutdown()
    logger.info("agent-mesh.shutdown.registry")

    uptime = round(time.monotonic() - _boot_time, 2)
    logger.info("agent-mesh.shutdown.complete", uptime_seconds=uptime)


# --- FastAPI App ---

app = FastAPI(
    title="SYSTVETAM Agent Mesh",
    description="16 AI agent sessions. One service. All receipted.",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Full mesh health — sessions, router, executor, heartbeat.
    Railway hits this for health checks.
    Tower Dashboard reads this for crew status.
    """
    settings = get_settings()

    # Determine mesh status
    if not _registry.is_initialized:
        status = MeshStatus.OFFLINE
    elif _registry.session_count < 16:
        status = MeshStatus.DEGRADED
    else:
        status = MeshStatus.ACTIVE

    return HealthResponse(
        status=status,
        sessions=_registry.session_count,
        mesh=status.value,
        zos_env=settings.zos_env,
        uptime_seconds=round(time.monotonic() - _boot_time, 2),
        sessions_detail=_registry.health_snapshot(),
    )


@app.get("/health/detailed")
async def health_detailed():
    """
    Extended health with router, executor, and heartbeat stats.
    Not called by Railway — used for debugging and monitoring.
    """
    settings = get_settings()
    return {
        "status": "ACTIVE" if _registry.is_initialized else "OFFLINE",
        "sessions": _registry.session_count,
        "zos_env": settings.zos_env,
        "uptime_seconds": round(time.monotonic() - _boot_time, 2),
        "router": _router.stats(),
        "executor": _executor.stats(),
        "heartbeat": _heartbeat.stats(),
        "sessions_detail": [s.to_health() for s in _registry.all_sessions()],
    }


@app.get("/")
async def root():
    """Identity endpoint."""
    return {
        "service": "agent-mesh",
        "version": "0.1.0",
        "system": "SYSTVETAM",
        "org": "Zentraux Group LLC",
        "sessions": _registry.session_count,
        "status": "ACTIVE" if _registry.is_initialized else "OFFLINE",
    }


@app.get("/crew")
async def list_crew():
    """All crew sessions with current status."""
    return {
        "count": _registry.session_count,
        "crew": [s.to_health() for s in _registry.all_sessions()],
    }


@app.get("/crew/{callsign}")
async def get_crew(callsign: str):
    """Single crew session detail."""
    session = _registry.get(callsign.upper())
    if session is None:
        return JSONResponse(
            status_code=404,
            content=MeshError(
                error="session_not_found",
                detail=f"No session for callsign: {callsign}",
                callsign=callsign,
            ).model_dump(mode="json"),
        )
    return session.to_health()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """No silent failures. Every error surfaced."""
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content=MeshError(
            error="internal_error",
            detail=str(exc),
        ).model_dump(mode="json"),
    )
