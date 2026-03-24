"""
SYSTVETAM — Central Dispatch
Zentraux Group LLC | FastAPI Application Entry Point

The spine. Routes tasks. Enforces state machine.
Generates all receipts. Feeds Tower Dashboard live.

Exposed via: api.zentrauxgroup.com (Cloudflare tunnel)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dispatch.config import settings
from dispatch.database import engine, async_session_factory
from dispatch.redis_client import redis_pool, init_redis, close_redis
from dispatch.routers import (
    auth,
    crew,
    gates,
    health,
    intelligence,
    receipts,
    tasks,
    websocket,
)


# ---------------------------------------------------------------------------
# Lifespan — DB engine init, Redis connect, graceful teardown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:  connect Redis, verify Postgres, log boot receipt.
    Shutdown: drain Redis, dispose engine, log shutdown receipt.
    """
    # — Startup —

    # Block 1: ENUM types only — tables are managed by Alembic pre-start
    try:
        from sqlalchemy import text as _text
        async with engine.begin() as _conn:
            _enum_stmts = [
                """DO $$ BEGIN
                CREATE TYPE crew_status AS ENUM ('ACTIVE','IDLE','EXECUTING','ERROR','OFFLINE');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;""",
                """DO $$ BEGIN
                CREATE TYPE execution_plane AS ENUM ('cloud','local');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;""",
                """DO $$ BEGIN
                CREATE TYPE task_status AS ENUM ('NEW','ASSIGNED','EXECUTING','QA_GATE','LEVI_GATE','DEPLOYING','COMPLETE','RECEIPTED','FAILED');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;""",
                """DO $$ BEGIN
                CREATE TYPE task_type AS ENUM ('STANDARD','INTELLIGENCE_BRIEF','BUILD_FROM_INTEL','OPPORTUNITY','GTM_CAMPAIGN','VOICE_OUTREACH','SECURITY_REVIEW','QA_EVALUATION');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;""",
                """DO $$ BEGIN
                CREATE TYPE receipt_type AS ENUM ('TASK_CREATED','TASK_ASSIGNED','TASK_COMPLETE','TASK_RECEIPTED','GATE_APPROVED','GATE_RETURNED','CREW_ACTIVATED','CREW_DEACTIVATED','QA_EVALUATION','QA_PASSED','QA_FAILED','SYSTEM_EVENT','ERROR_LOGGED','CHANGE_REQUEST','VENDOR_ONBOARD','FINANCIAL_APPROVAL');
                EXCEPTION WHEN duplicate_object THEN null;
                END $$;""",
            ]
            for _stmt in _enum_stmts:
                await _conn.execute(_text(_stmt))
        print("[DISPATCH] ENUM types verified/created")
        print("[DISPATCH] Schema managed by Alembic — tables pre-created at container start")
    except Exception as _e:
        print(f"[DISPATCH] ENUM warning: {_e}")

    # Block 2: Auto-seed crew on first boot (idempotent — skips if crew exists)
    try:
        from sqlalchemy import select, func
        from dispatch.models.crew_member import CrewMember
        async with async_session_factory() as _seed_session:
            result = await _seed_session.execute(select(func.count()).select_from(CrewMember))
            crew_count = result.scalar()
        if crew_count == 0:
            print("[DISPATCH] No crew found — running seed script...")
            import sys
            sys.path.insert(0, "/app")
            from dispatch.scripts.seed_crew import seed_crew
            await seed_crew()
            print("[DISPATCH] Crew seeded — 16 operators online")
        else:
            print(f"[DISPATCH] Crew roster: {crew_count} operators present — skipping seed")
    except Exception as _seed_err:
        print(f"[DISPATCH] WARNING: Auto-seed failed: {_seed_err}")

    await init_redis()
    app.state.redis = redis_pool

    # Verify Postgres is reachable (non-fatal — app starts even if DB is warming up)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        print("[DISPATCH] Postgres reachable — startup verified")
    except Exception as e:
        print(f"[DISPATCH] WARNING: Postgres unreachable at startup: {e}")
        print("[DISPATCH] Continuing — /health will serve, /status will report degraded")

    # Publish system boot event on Redis for any Tower Dashboard listeners
    if redis_pool:
        await redis_pool.publish(
            "system_events",
            '{"event":"DISPATCH_ONLINE","ts":"'
            + datetime.now(timezone.utc).isoformat()
            + '"}',
        )

    yield

    # — Shutdown —
    await close_redis()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Systvetam Central Dispatch",
    description=(
        "Task routing, state machine enforcement, receipt generation, "
        "and live WebSocket feed for Zentraux Group LLC."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.ZOS_ENV != "production" else None,
    redoc_url="/redoc" if settings.ZOS_ENV != "production" else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS — locked to known origins in production
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS: list[str] = settings.allowed_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


# ---------------------------------------------------------------------------
# Request ID injection (traceability — every request receipted if needed)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Routers — every endpoint lives in its module
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["Tasks"],
)
app.include_router(
    crew.router,
    prefix="/crew",
    tags=["Crew"],
)
app.include_router(
    gates.router,
    prefix="/gates",
    tags=["Gates"],
)
app.include_router(
    receipts.router,
    prefix="/receipts",
    tags=["Receipts"],
)
app.include_router(
    intelligence.router,
    prefix="/intelligence",
    tags=["Intelligence"],
)
app.include_router(
    websocket.router,
    tags=["WebSocket"],
)


# ---------------------------------------------------------------------------
# Global exception handler — doctrine violations surface cleanly
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from dispatch.state_machine import DoctrineViolation

    if isinstance(exc, DoctrineViolation):
        return JSONResponse(
            status_code=409,
            content={
                "error": "DOCTRINE_VIOLATION",
                "detail": str(exc),
                "sop_reference": getattr(exc, "sop_reference", None),
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "detail": "Central Dispatch encountered an unrecoverable error.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ---------------------------------------------------------------------------
# Uvicorn entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "dispatch.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ZOS_ENV == "development",
        log_level="info",
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )
