"""
mesh/router.py — SYSTVETAM Task Router
Redis pattern subscriber on dept:* channels.
Routes inbound tasks to the correct AgentSession via SessionRegistry.
Hands off execution to executor.py — never blocks the subscriber loop.

Dead letter handling: if callsign not found or payload malformed,
log the failure and continue. The subscriber never dies on bad input.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import redis.asyncio as aioredis
import structlog

from mesh.config import get_settings
from mesh.models import TaskPayload

if TYPE_CHECKING:
    from mesh.executor import TaskExecutor
    from mesh.registry import SessionRegistry

logger = structlog.get_logger("agent-mesh.router")


class TaskRouter:
    """
    Subscribes to Redis dept:* channels via pattern subscribe.
    On each message: parse → validate → route to executor.

    Lifecycle:
        1. start(registry, executor) — connect Redis, subscribe, spawn listener
        2. _listener_loop() — runs forever, dispatches tasks as fire-and-forget
        3. stop() — cancel listener, unsubscribe, close Redis
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._registry: SessionRegistry | None = None
        self._executor: TaskExecutor | None = None
        self._running: bool = False

        # Metrics
        self.tasks_routed: int = 0
        self.tasks_dead_lettered: int = 0
        self.tasks_malformed: int = 0

    async def start(
        self,
        registry: SessionRegistry,
        executor: TaskExecutor,
    ) -> None:
        """
        Connect to Redis, pattern-subscribe to dept:*, spawn listener.
        """
        settings = get_settings()
        self._registry = registry
        self._executor = executor

        self._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            retry_on_error=[ConnectionError, TimeoutError],
            socket_connect_timeout=10.0,
            socket_timeout=30.0,
        )

        # Verify connection
        try:
            await self._redis.ping()
            logger.info("router.redis.connected", url=settings.redis_url[:30] + "...")
        except Exception as e:
            logger.error("router.redis.connect_failed", error=str(e))
            raise

        # Pattern subscribe to all department channels
        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe("dept:*")
        logger.info("router.subscribed", pattern="dept:*")

        # Spawn listener as background task
        self._running = True
        self._listener_task = asyncio.create_task(
            self._listener_loop(),
            name="task-router-listener",
        )
        logger.info("router.started")

    async def _listener_loop(self) -> None:
        """
        Main subscriber loop. Runs until stop() is called.
        Each message is dispatched as a fire-and-forget task —
        the listener never blocks waiting for execution to complete.
        """
        logger.info("router.listener.running")

        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    # No message within timeout — loop back
                    await asyncio.sleep(0.1)
                    continue

                if message["type"] != "pmessage":
                    continue

                channel = message.get("channel", "")
                data = message.get("data", "")

                log = logger.bind(channel=channel)

                # Parse task payload
                task = self._parse_payload(data, log)
                if task is None:
                    self.tasks_malformed += 1
                    continue

                # Route to session
                session = self._registry.get(task.callsign)
                if session is None:
                    # Dead letter — callsign not in mesh
                    self.tasks_dead_lettered += 1
                    log.warning(
                        "router.dead_letter",
                        callsign=task.callsign,
                        task_id=task.task_id,
                        reason="callsign not found in registry",
                    )
                    continue

                # Fire-and-forget — executor handles the task async
                self.tasks_routed += 1
                asyncio.create_task(
                    self._executor.run(session, task),
                    name=f"exec-{task.callsign}-{task.task_id[:8]}",
                )

                log.info(
                    "router.dispatched",
                    callsign=task.callsign,
                    task_id=task.task_id,
                    title=task.title[:80],
                    routed_total=self.tasks_routed,
                )

            except asyncio.CancelledError:
                logger.info("router.listener.cancelled")
                break
            except Exception as e:
                # Never let the listener die on a single bad message
                logger.error("router.listener.error", error=str(e))
                await asyncio.sleep(1.0)

        logger.info("router.listener.stopped")

    def _parse_payload(
        self,
        raw: str,
        log: structlog.stdlib.BoundLogger,
    ) -> TaskPayload | None:
        """
        Parse raw Redis message data into a TaskPayload.
        Returns None on failure — caller handles dead letter.
        """
        if not raw:
            log.warning("router.parse.empty_message")
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            log.warning("router.parse.invalid_json", error=str(e), raw=raw[:200])
            return None

        try:
            return TaskPayload.model_validate(data)
        except Exception as e:
            log.warning(
                "router.parse.validation_failed",
                error=str(e),
                keys=list(data.keys()) if isinstance(data, dict) else "not-a-dict",
            )
            return None

    async def stop(self) -> None:
        """
        Graceful shutdown: cancel listener, unsubscribe, close Redis.
        """
        self._running = False

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            try:
                await self._pubsub.punsubscribe("dept:*")
                await self._pubsub.close()
            except Exception as e:
                logger.warning("router.stop.pubsub_error", error=str(e))

        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning("router.stop.redis_error", error=str(e))

        logger.info(
            "router.stopped",
            tasks_routed=self.tasks_routed,
            dead_lettered=self.tasks_dead_lettered,
            malformed=self.tasks_malformed,
        )

    def stats(self) -> dict:
        """Router metrics for /health."""
        return {
            "tasks_routed": self.tasks_routed,
            "tasks_dead_lettered": self.tasks_dead_lettered,
            "tasks_malformed": self.tasks_malformed,
            "running": self._running,
        }
