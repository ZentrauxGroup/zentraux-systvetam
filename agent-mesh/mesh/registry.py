"""
mesh/registry.py — SYSTVETAM SessionRegistry
Manages the lifecycle of all 16 agent sessions.

FOUNDER (AGT-001) excluded — Levi is Human Architect, not an AI session.
ZENTRAUX (Agent Zero) excluded — already running as Orchestrator.
Mesh count = 16: AGT-002 through AGT-017 (SCOPE).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog

from mesh.config import get_settings, CREW_REGISTRY
from mesh.models import CrewMemberConfig, CrewStatus, SessionHealth
from mesh.session import AgentSession, AgentSessionError

logger = structlog.get_logger("agent-mesh.registry")

# Callsigns excluded from mesh sessions
EXCLUDED_CALLSIGNS: frozenset[str] = frozenset({"FOUNDER", "ZENTRAUX"})


class SessionRegistry:
    """
    Singleton registry of all active AgentSession instances.

    Lifecycle:
        1. initialize() — filter crew, load roles, create sessions, open HTTP pool
        2. get(callsign) — retrieve session by callsign
        3. get_by_department(dept) — list sessions in a department
        4. shutdown() — close HTTP pool, mark all sessions OFFLINE

    All 16 sessions share one httpx.AsyncClient connection pool.
    Sessions are persistent — not re-created per task.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}
        self._http_client: httpx.AsyncClient | None = None
        self._initialized: bool = False

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self, roles_dir: Path | None = None) -> None:
        """
        Boot all 16 agent sessions.

        1. Filter CREW_REGISTRY — exclude FOUNDER and ZENTRAUX
        2. Resolve model per callsign (FORGE → Opus, rest → Sonnet)
        3. Create AgentSession per crew member
        4. Load role file into each session
        5. Open shared HTTP connection pool
        6. Inject HTTP client into each session
        7. Set all sessions to ACTIVE

        Raises AgentSessionError if any role file is missing.
        """
        settings = get_settings()
        if roles_dir is None:
            roles_dir = settings.role_files_dir

        logger.info(
            "registry.init.start",
            crew_total=len(CREW_REGISTRY),
            excluded=list(EXCLUDED_CALLSIGNS),
            roles_dir=str(roles_dir),
        )

        # Filter crew — exclude FOUNDER and ZENTRAUX
        eligible_crew = [
            c for c in CREW_REGISTRY
            if c["callsign"] not in EXCLUDED_CALLSIGNS
        ]

        logger.info(
            "registry.init.filtered",
            eligible=len(eligible_crew),
            excluded_count=len(CREW_REGISTRY) - len(eligible_crew),
        )

        # Build CrewMemberConfig with model routing
        configs: list[CrewMemberConfig] = []
        for crew in eligible_crew:
            model = settings.model_for_callsign(crew["callsign"])
            configs.append(
                CrewMemberConfig(
                    agt_id=crew["agt_id"],
                    callsign=crew["callsign"],
                    name=crew["name"],
                    department=crew["department"],
                    role_file=crew["role_file"],
                    model=model,
                )
            )

        # Create sessions and load role files
        failed: list[str] = []
        for config in configs:
            session = AgentSession(config)
            try:
                session.load_role(roles_dir)
                self._sessions[session.callsign] = session
            except AgentSessionError as e:
                logger.error(
                    "registry.init.role_load_failed",
                    callsign=config.callsign,
                    error=str(e),
                )
                failed.append(config.callsign)

        if failed:
            logger.warning(
                "registry.init.partial",
                loaded=len(self._sessions),
                failed=failed,
            )

        # Open shared HTTP connection pool
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=120.0,
                write=30.0,
                pool=10.0,
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )

        # Inject HTTP client and activate all loaded sessions
        for session in self._sessions.values():
            session.set_http_client(self._http_client)
            session.status = CrewStatus.ACTIVE

        self._initialized = True

        # Log the full roster with model assignments
        for session in self._sessions.values():
            opus_tag = " ** OPUS **" if "opus" in session.model else ""
            logger.info(
                "registry.session.ready",
                callsign=session.callsign,
                agt_id=session.agt_id,
                name=session.name,
                department=session.department,
                model=session.model + opus_tag,
            )

        logger.info(
            "registry.init.complete",
            sessions_ready=len(self._sessions),
            message=f"{len(self._sessions)} sessions ready",
        )

    def get(self, callsign: str) -> AgentSession | None:
        """Retrieve session by callsign. Returns None if not found."""
        return self._sessions.get(callsign.upper())

    def get_by_department(self, department: str) -> list[AgentSession]:
        """List all sessions in a given department."""
        return [
            s for s in self._sessions.values()
            if s.department == department.lower()
        ]

    def get_by_agt_id(self, agt_id: str) -> AgentSession | None:
        """Retrieve session by AGT-ID. Linear scan — 16 entries, negligible."""
        for session in self._sessions.values():
            if session.agt_id == agt_id:
                return session
        return None

    def all_sessions(self) -> list[AgentSession]:
        """All active sessions, sorted by AGT-ID."""
        return sorted(self._sessions.values(), key=lambda s: s.agt_id)

    def all_callsigns(self) -> list[str]:
        """All registered callsigns."""
        return sorted(self._sessions.keys())

    def active_callsigns(self) -> list[str]:
        """Callsigns with status ACTIVE or EXECUTING."""
        return [
            s.callsign for s in self._sessions.values()
            if s.status in (CrewStatus.ACTIVE, CrewStatus.EXECUTING)
        ]

    def health_snapshot(self) -> list[SessionHealth]:
        """Build health detail for every session — used by /health endpoint."""
        return [
            SessionHealth(
                callsign=s.callsign,
                agt_id=s.agt_id,
                name=s.name,
                department=s.department,
                model=s.model,
                status=s.status,
                tasks_completed=s.tasks_completed,
                last_task_at=s.last_task_at,
            )
            for s in self.all_sessions()
        ]

    async def shutdown(self) -> None:
        """
        Graceful shutdown. Mark all sessions OFFLINE, close HTTP pool.
        Called during FastAPI lifespan shutdown.
        """
        logger.info("registry.shutdown.start", sessions=len(self._sessions))

        for session in self._sessions.values():
            session.status = CrewStatus.OFFLINE

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._initialized = False
        logger.info("registry.shutdown.complete")

    def __repr__(self) -> str:
        return (
            f"SessionRegistry(sessions={len(self._sessions)}, "
            f"initialized={self._initialized})"
        )
