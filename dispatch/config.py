"""
SYSTVETAM — Central Dispatch Configuration
Zentraux Group LLC

All configuration loaded from environment variables via pydantic-settings.
No hardcoded secrets. No defaults for sensitive values.

Production env:  api.zentrauxgroup.com (Cloudflare tunnel)
Local dev:       docker-compose on zos-mesh network
"""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Single source of truth for all Central Dispatch configuration.
    Every value comes from environment or .env file — no exceptions.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Core Identity
    # -----------------------------------------------------------------------
    ZOS_ENV: str = "development"  # development | staging | production
    DISPATCH_URL: str = "http://localhost:8000"
    LEVI_AGENT_ID: str = "AGT-001"

    # -----------------------------------------------------------------------
    # PostgreSQL — async via asyncpg
    # -----------------------------------------------------------------------
    DATABASE_URL: str  # postgresql+asyncpg://zos:{pw}@postgres/systvetam

    @field_validator("DATABASE_URL")
    @classmethod
    def enforce_async_driver(cls, v: str) -> str:
        """Doctrine: all DB access is async. Reject synchronous drivers."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use postgresql+asyncpg:// driver. "
                "Synchronous access violates Systvetam architecture."
            )
        return v

    # -----------------------------------------------------------------------
    # Redis — pub/sub message bus
    # -----------------------------------------------------------------------
    REDIS_URL: str = "redis://redis:6379"

    # -----------------------------------------------------------------------
    # Auth — JWT + RBAC
    # -----------------------------------------------------------------------
    JWT_SECRET: str  # 256-bit generated — no default
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480  # 8 hours — one full shift

    # -----------------------------------------------------------------------
    # Execution Planes
    # -----------------------------------------------------------------------
    # Plane A (Cloud): OpenRouter → Claude Sonnet 4.6
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4-20250514"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Plane B (Local): Ollama → qwen3:8b
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen3:8b"

    # Which plane fires first — cloud or local
    DEFAULT_PLANE: str = "cloud"  # cloud | local

    # -----------------------------------------------------------------------
    # CORS — allowed origins (parsed from comma-separated string)
    # -----------------------------------------------------------------------
    ALLOWED_ORIGINS: str = (
        "https://tower.zentrauxgroup.com,"
        "https://api.zentrauxgroup.com"
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list for CORS middleware."""
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.ZOS_ENV == "development":
            origins.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ])
        return origins

    # -----------------------------------------------------------------------
    # Webhooks & Notifications
    # -----------------------------------------------------------------------
    LEVI_GATE_WEBHOOK: str = ""  # Discord/Slack webhook for gate alerts

    # -----------------------------------------------------------------------
    # Agent Mesh
    # -----------------------------------------------------------------------
    DOCKER_NETWORK: str = "zos-mesh"
    CREW_ROLES_PATH: str = "/crew-roles"  # mounted read-only in container

    # -----------------------------------------------------------------------
    # Receipt Engine
    # -----------------------------------------------------------------------
    RECEIPT_PREFIX: str = "RCPT"

    # -----------------------------------------------------------------------
    # Intelligence (Clyde)
    # -----------------------------------------------------------------------
    CLYDE_SERVICE_URL: str = "http://clyde:8006"
    SIGNAL_THRESHOLD: float = 0.70  # minimum signal_strength to generate brief

    # -----------------------------------------------------------------------
    # Rate Limiting
    # -----------------------------------------------------------------------
    TASK_CREATE_RATE_LIMIT: int = 60  # max POST /tasks per minute

    @property
    def is_production(self) -> bool:
        return self.ZOS_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.ZOS_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings singleton. Call this everywhere —
    never instantiate Settings() directly.
    """
    return Settings()


# Module-level convenience reference used by main.py and routers
settings = get_settings()
