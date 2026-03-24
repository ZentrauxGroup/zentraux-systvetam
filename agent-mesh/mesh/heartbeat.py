"""
mesh/heartbeat.py — SYSTVETAM Heartbeat Service
Background loop that pings Central Dispatch every 30 seconds
for each of the 16 active sessions.

This is what turns the Tower Lobby dots gold.

Dispatch endpoint: PATCH /crew/{callsign}/status
Auth: Bearer {MESH_SERVICE_TOKEN}
Body: {"status": "ACTIVE", "last_seen": "ISO timestamp"}

Non-fatal if Dispatch is unreachable — log and continue.
The heartbeat never crashes the mesh. It degrades gracefully.
If it can't reach Dispatch for >90s, Dispatch marks crew OFFLINE.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
import structlog

from mesh.config import get_settings
from mesh.models import CrewStatus

if TYPE_CHECKING:
    from mesh.registry import SessionRegistry

logger = structlog.get_logger("agent-mesh.heartbeat")


class HeartbeatService:
    """
    Sends periodic status updates to Central Dispatch for every session.

    Lifecycle:
        1. start(registry) — open HTTP client, spawn background loop
        2. _heartbeat_loop() — runs forever at configured interval
        3. stop() — cancel loop, close HTTP client

    Each beat sends one PATCH per active session.
    Failures are logged but never propagated — the beat continues.
    """

    def __init__(self) -> None:
        self._registry: SessionRegistry | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._loop_task: asyncio.Task | None = None
        self._running: bool = False

        # Metrics
        self.beats_sent: int = 0
        self.beats_failed: int = 0
        self.cycles_completed: int = 0

    async def start(self, registry: SessionRegistry) -> None:
        """Open HTTP client, spawn heartbeat loop."""
        self._registry = registry

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=10.0,
                write=5.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=3,
            ),
        )

        self._running = True
        self._loop_task = asyncio.create_task(
            self._heartbeat_loop(),
            name="heartbeat-loop",
        )

        logger.info("heartbeat.started")

    async def _heartbeat_loop(self) -> None:
        """
        Main loop — runs every HEARTBEAT_INTERVAL_SECONDS.
        Sends status for all sessions concurrently via gather.
        """
        settings = get_settings()
        interval = settings.heartbeat_interval_seconds

        logger.info(
            "heartbeat.loop.running",
            interval_seconds=interval,
        )

        while self._running:
            try:
                await self._send_all_heartbeats()
                self.cycles_completed += 1
            except asyncio.CancelledError:
                logger.info("heartbeat.loop.cancelled")
                break
            except Exception as e:
                # Never let the loop die
                logger.error("heartbeat.loop.error", error=str(e))

            # Sleep for the interval, but check _running to allow quick shutdown
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

        logger.info("heartbeat.loop.stopped")

    async def _send_all_heartbeats(self) -> None:
        """
        Send heartbeat for every session concurrently.
        Uses asyncio.gather with return_exceptions=True so one
        failure doesn't block others.
        """
        if self._registry is None:
            return

        sessions = self._registry.all_sessions()
        if not sessions:
            return

        tasks = [
            self._send_one_heartbeat(session.callsign, session.status)
            for session in sessions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is not True)

        if failures > 0:
            logger.warning(
                "heartbeat.cycle.partial",
                successes=successes,
                failures=failures,
                cycle=self.cycles_completed + 1,
            )
        else:
            logger.debug(
                "heartbeat.cycle.complete",
                sessions=successes,
                cycle=self.cycles_completed + 1,
            )

    async def _send_one_heartbeat(
        self,
        callsign: str,
        status: CrewStatus,
    ) -> bool:
        """
        PATCH one crew member's status to Dispatch.
        Returns True on success, False on failure.
        """
        if self._http_client is None:
            return False

        settings = get_settings()
        url = f"{settings.dispatch_url}/crew/{callsign}/status"

        headers = {
            "Content-Type": "application/json",
            "X-Service": "agent-mesh",
        }
        if settings.mesh_service_token:
            headers["Authorization"] = f"Bearer {settings.mesh_service_token}"

        payload = {
            "status": status.value,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = await self._http_client.patch(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            self.beats_sent += 1
            return True

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else 0
            self.beats_failed += 1
            # Only log at warning for non-404 — 404 means Dispatch
            # hasn't seeded this callsign yet (expected during first boot)
            if status_code == 404:
                logger.debug(
                    "heartbeat.send.not_found",
                    callsign=callsign,
                    url=url,
                )
            else:
                logger.warning(
                    "heartbeat.send.http_error",
                    callsign=callsign,
                    status_code=status_code,
                    url=url,
                )
            return False

        except httpx.RequestError as e:
            self.beats_failed += 1
            logger.warning(
                "heartbeat.send.request_error",
                callsign=callsign,
                error=str(e),
            )
            return False

        except Exception as e:
            self.beats_failed += 1
            logger.error(
                "heartbeat.send.unexpected",
                callsign=callsign,
                error=str(e),
            )
            return False

    async def stop(self) -> None:
        """Cancel loop, close HTTP client."""
        self._running = False

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info(
            "heartbeat.stopped",
            beats_sent=self.beats_sent,
            beats_failed=self.beats_failed,
            cycles=self.cycles_completed,
        )

    def stats(self) -> dict:
        """Heartbeat metrics for /health."""
        return {
            "beats_sent": self.beats_sent,
            "beats_failed": self.beats_failed,
            "cycles_completed": self.cycles_completed,
            "running": self._running,
        }
