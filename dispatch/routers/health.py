"""
SYSTVETAM — Health & Status Router
Zentraux Group LLC

/health  — lightweight watchdog probe (Railway, Cloudflare, Docker HEALTHCHECK)
/status  — full system snapshot (DB, Redis, config, uptime)

These are the first endpoints that prove the spine is alive.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.config import settings
from dispatch.database import get_db
from dispatch.redis_client import get_redis

router = APIRouter()

BOOT_TIME = datetime.now(timezone.utc)


@router.get("/health", tags=["System"])
async def health():
    """
    Lightweight health check — returns 200 if the process is alive.
    Used by Railway health checks, Cloudflare tunnel origin probe,
    Docker HEALTHCHECK, and zos_bot_watchdog.sh.
    """
    return {
        "status": "operational",
        "service": "systvetam-central-dispatch",
        "version": "1.0.0",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status", tags=["System"])
async def status(db: AsyncSession = Depends(get_db)):
    """
    Full system snapshot — probes DB, Redis, reports config.
    Swagger docs gated by ZOS_ENV in main.py, but this endpoint
    is always available for internal monitoring.
    """
    # Postgres probe
    db_ok = False
    try:
        result = await db.execute(text("SELECT 1"))
        db_ok = result.scalar() == 1
    except Exception:
        pass

    # Redis probe
    redis_ok = False
    redis = get_redis()
    if redis is not None:
        try:
            await redis.ping()
            redis_ok = True
        except Exception:
            pass

    uptime_seconds = (datetime.now(timezone.utc) - BOOT_TIME).total_seconds()

    all_ok = db_ok and redis_ok

    return {
        "status": "operational" if all_ok else "degraded",
        "service": "systvetam-central-dispatch",
        "version": "1.0.0",
        "environment": settings.ZOS_ENV,
        "uptime_seconds": round(uptime_seconds, 1),
        "checks": {
            "postgres": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable",
        },
        "config": {
            "default_plane": settings.DEFAULT_PLANE,
            "dispatch_url": settings.DISPATCH_URL,
            "signal_threshold": settings.SIGNAL_THRESHOLD,
        },
        "ts": datetime.now(timezone.utc).isoformat(),
    }
