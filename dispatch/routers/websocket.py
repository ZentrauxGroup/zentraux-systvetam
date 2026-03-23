"""
SYSTVETAM — WebSocket Router
Zentraux Group LLC

Live feed for Tower Dashboard. Subscribes to Redis pub/sub channels
and relays every event to connected WebSocket clients in real time.

No polling. No 5-second refresh. The Tower sees state change
the instant it happens. This is what makes the dashboard alive.

Channels subscribed:
  - task_events      : state transitions
  - gate_events      : gate created / decided
  - receipts         : receipt auto-filed
  - crew_events      : crew activation / deactivation
  - system_events    : dispatch online/offline, errors

Endpoints from Engineering Directive v1.0:
  WS  /ws            Tower Dashboard live feed
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dispatch.redis_client import subscribe, get_redis

router = APIRouter()
logger = logging.getLogger("dispatch.websocket")

# All channels the Tower Dashboard consumes
DASHBOARD_CHANNELS = [
    "task_events",
    "gate_events",
    "receipts",
    "crew_events",
    "system_events",
]


# ---------------------------------------------------------------------------
# Connection Manager — tracks active Tower Dashboard sessions
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for the Tower Dashboard.
    Supports broadcast to all connected clients.
    """

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(
            "Tower Dashboard connected. Active sessions: %d", len(self.active)
        )

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)
        logger.info(
            "Tower Dashboard disconnected. Active sessions: %d", len(self.active)
        )

    async def broadcast(self, message: str):
        """Send message to all connected clients. Drop dead connections."""
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WS /ws — Tower Dashboard Live Feed
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def tower_dashboard_feed(ws: WebSocket):
    """
    Main WebSocket endpoint for the Tower Dashboard.

    On connect:
      1. Accept connection
      2. Send initial handshake with server time and status
      3. Subscribe to all Redis pub/sub channels
      4. Relay every Redis message to the client
      5. Listen for client pings / commands

    On disconnect:
      Clean up subscription and connection.
    """
    await manager.connect(ws)

    # Send handshake so the dashboard knows the connection is live
    await ws.send_text(json.dumps({
        "event": "CONNECTED",
        "service": "systvetam-central-dispatch",
        "channels": DASHBOARD_CHANNELS,
        "ts": datetime.now(timezone.utc).isoformat(),
    }))

    pubsub = None
    relay_task = None

    try:
        # Subscribe to Redis channels
        redis = get_redis()
        if redis is None:
            # No Redis — fall back to heartbeat-only mode
            await _heartbeat_loop(ws)
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(*DASHBOARD_CHANNELS)

        # Spawn relay coroutine — reads Redis, pushes to WebSocket
        relay_task = asyncio.create_task(_redis_relay(pubsub, ws))

        # Main loop — listen for client messages (ping, commands)
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
                await _handle_client_message(ws, data)
            except asyncio.TimeoutError:
                # No client message in 60s — send heartbeat
                await ws.send_text(json.dumps({
                    "event": "HEARTBEAT",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        # Cleanup
        if relay_task and not relay_task.done():
            relay_task.cancel()
            try:
                await relay_task
            except asyncio.CancelledError:
                pass

        if pubsub:
            await pubsub.unsubscribe(*DASHBOARD_CHANNELS)
            await pubsub.aclose()

        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Redis → WebSocket relay
# ---------------------------------------------------------------------------

async def _redis_relay(pubsub, ws: WebSocket):
    """
    Read messages from Redis pub/sub and forward to the WebSocket client.
    Runs as a background task alongside the main client message loop.
    """
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await ws.send_text(message["data"])
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.warning("Redis relay error: %s", e)


# ---------------------------------------------------------------------------
# Client message handler
# ---------------------------------------------------------------------------

async def _handle_client_message(ws: WebSocket, data: str):
    """
    Handle incoming messages from the Tower Dashboard client.
    Currently supports:
      - PING: respond with PONG
      - SUBSCRIBE: add channels (future use)
    """
    try:
        msg = json.loads(data)
    except json.JSONDecodeError:
        return

    event = msg.get("event", "").upper()

    if event == "PING":
        await ws.send_text(json.dumps({
            "event": "PONG",
            "ts": datetime.now(timezone.utc).isoformat(),
        }))


# ---------------------------------------------------------------------------
# Heartbeat fallback — when Redis is unavailable
# ---------------------------------------------------------------------------

async def _heartbeat_loop(ws: WebSocket):
    """
    If Redis is down, keep the WebSocket alive with heartbeats.
    The dashboard won't get live events but stays connected.
    """
    try:
        await ws.send_text(json.dumps({
            "event": "WARNING",
            "detail": "Redis unavailable. Live events disabled. Heartbeat only.",
            "ts": datetime.now(timezone.utc).isoformat(),
        }))
        while True:
            await asyncio.sleep(30)
            await ws.send_text(json.dumps({
                "event": "HEARTBEAT",
                "ts": datetime.now(timezone.utc).isoformat(),
            }))
    except (WebSocketDisconnect, Exception):
        manager.disconnect(ws)
