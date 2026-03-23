"""
SYSTVETAM — Redis Client
Zentraux Group LLC

Redis serves as the pub/sub message bus for the Systvetam.
Every state transition, receipt, and gate event publishes here.
Tower Dashboard consumes via WebSocket relay.

Channels:
  - task_events     : state transitions (consumed by /ws)
  - receipts        : receipt auto-generation events
  - gate_events     : new gate / gate decision notifications
  - crew_events     : crew activation / deactivation
  - system_events   : DISPATCH_ONLINE, DISPATCH_SHUTDOWN, errors
  - intelligence    : Clyde brief submissions
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as aioredis

from dispatch.config import settings

logger = logging.getLogger("dispatch.redis")

# ---------------------------------------------------------------------------
# Module-level pool — initialized in lifespan, used everywhere
# ---------------------------------------------------------------------------

redis_pool: Optional[aioredis.Redis] = None


# ---------------------------------------------------------------------------
# Lifecycle — called from main.py lifespan
# ---------------------------------------------------------------------------

async def init_redis() -> aioredis.Redis:
    """
    Create the async Redis connection pool.
    Called once at startup from the FastAPI lifespan handler.
    """
    global redis_pool
    try:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        # Verify connection
        await redis_pool.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return redis_pool

    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.error("Redis connection failed: %s — operating without pub/sub", e)
        redis_pool = None
        raise


async def close_redis() -> None:
    """
    Drain and close the Redis pool.
    Called at shutdown from the FastAPI lifespan handler.
    """
    global redis_pool
    if redis_pool is not None:
        await redis_pool.aclose()
        redis_pool = None
        logger.info("Redis connection closed.")


# ---------------------------------------------------------------------------
# Publish helper — used by state_machine, receipt_engine, gates
# ---------------------------------------------------------------------------

CHANNELS = {
    "task_events",
    "receipts",
    "gate_events",
    "crew_events",
    "system_events",
    "intelligence",
}


async def publish(channel: str, payload: dict[str, Any]) -> bool:
    """
    Publish a JSON message to a Redis pub/sub channel.

    Every published message includes a timestamp and channel tag
    for traceability. Returns True if published, False if Redis
    is unavailable (graceful degradation — dispatch still works
    without real-time push, Tower Dashboard just won't update live).
    """
    if redis_pool is None:
        logger.warning(
            "Redis unavailable — dropping message on channel '%s'", channel
        )
        return False

    if channel not in CHANNELS:
        logger.warning(
            "Unknown Redis channel '%s' — publishing anyway. "
            "Consider adding to CHANNELS set.",
            channel,
        )

    message = {
        "channel": channel,
        "ts": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    try:
        listeners = await redis_pool.publish(channel, json.dumps(message))
        logger.debug(
            "Published to '%s' (%d listeners): %s",
            channel,
            listeners,
            payload.get("event", "unknown"),
        )
        return True

    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.error("Redis publish failed on '%s': %s", channel, e)
        return False


# ---------------------------------------------------------------------------
# Subscribe helper — used by websocket router to relay to clients
# ---------------------------------------------------------------------------

async def subscribe(*channels: str) -> aioredis.client.PubSub:
    """
    Create a Redis PubSub subscription on one or more channels.
    Caller is responsible for iterating messages and closing.

    Usage in websocket.py:
        pubsub = await subscribe("task_events", "gate_events")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await ws.send_text(message["data"])
    """
    if redis_pool is None:
        raise ConnectionError(
            "Redis not available — cannot subscribe. "
            "WebSocket relay requires active Redis connection."
        )

    pubsub = redis_pool.pubsub()
    await pubsub.subscribe(*channels)
    return pubsub


# ---------------------------------------------------------------------------
# Convenience — get pool reference for direct use
# ---------------------------------------------------------------------------

def get_redis() -> Optional[aioredis.Redis]:
    """Return the current Redis pool or None if unavailable."""
    return redis_pool
