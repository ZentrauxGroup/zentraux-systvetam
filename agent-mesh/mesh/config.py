"""
mesh/config.py — SYSTVETAM Agent Mesh Configuration
Model governance locked by Architect. Do not override.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration sourced from environment variables.
    Railway injects these at deploy time.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- OpenRouter ---
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # --- Model Governance (LOCKED) ---
    # All 16 crew on Sonnet. Marcus Reed (FORGE) on Opus.
    default_model: str = "anthropic/claude-sonnet-4-5"
    opus_model: str = "anthropic/claude-opus-4-5"
    opus_callsigns: set[str] = {"FORGE"}

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    # --- Central Dispatch ---
    dispatch_url: str = "https://dispatch-production-7190.up.railway.app"
    mesh_service_token: str = ""

    # --- ZOS ---
    zos_env: str = "development"
    port: int = 8001

    # --- Agent Mesh Tuning ---
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 90
    max_task_tokens: int = 4096
    role_files_dir: Path = Path("/app/roles")

    @field_validator("opus_callsigns", mode="before")
    @classmethod
    def parse_opus_callsigns(cls, v: str | set) -> set[str]:
        """Accept comma-separated string from env or set directly."""
        if isinstance(v, str):
            return {s.strip().upper() for s in v.split(",") if s.strip()}
        return {s.upper() for s in v}

    def model_for_callsign(self, callsign: str) -> str:
        """
        Route callsign to model. FORGE gets Opus. Everyone else: Sonnet.
        This is doctrine — not a preference.
        """
        if callsign.upper() in self.opus_callsigns:
            return self.opus_model
        return self.default_model

    @property
    def is_production(self) -> bool:
        return self.zos_env == "production"


# --- Canonical Crew Registry ---
# Source of truth: ROLE__INDEX__v02.md
# AGT-IDs and callsigns match canonical role files, NOT the Sprint 5 brief table
# (brief table has ID mismatches — flagged to Architect)

CREW_REGISTRY: list[dict[str, str]] = [
    {"agt_id": "AGT-001", "callsign": "FOUNDER",  "name": "Levi C. Haynes",      "department": "hq",           "role_file": "ROLE__Levi-Haynes__v02.md"},
    {"agt_id": "AGT-002", "callsign": "NOVA",     "name": "Dr. Isabella Reyes",   "department": "strategy",     "role_file": "ROLE__Isabella-Reyes__v02.md"},
    {"agt_id": "AGT-003", "callsign": "ANCHOR",   "name": "Victoria Langford",    "department": "governance",   "role_file": "ROLE__Tori-Langford__v02.md"},
    {"agt_id": "AGT-004", "callsign": "KIM",      "name": "Kimberly Harlan",      "department": "finance",      "role_file": "ROLE__Kim-Harlan__v02.md"},
    {"agt_id": "AGT-005", "callsign": "FORGE",    "name": "Marcus Reed",          "department": "engineering",  "role_file": "ROLE__Marcus-Reed__v02.md"},
    {"agt_id": "AGT-006", "callsign": "JAX",      "name": "Jaxon Harlow",         "department": "engineering",  "role_file": "ROLE__Jax-Harlow__v02.md"},
    {"agt_id": "AGT-007", "callsign": "FRAME",    "name": "Sophia Navarro",       "department": "engineering",  "role_file": "ROLE__Sophia-Navarro__v02.md"},
    {"agt_id": "AGT-008", "callsign": "RYE",      "name": "Riley Kim",            "department": "security",     "role_file": "ROLE__Rye-Kim__v02.md"},
    {"agt_id": "AGT-009", "callsign": "LEN",      "name": "Lena Moreau",          "department": "engineering",  "role_file": "ROLE__Lena-Moreau__v02.md"},
    {"agt_id": "AGT-010", "callsign": "SIGNAL",   "name": "Dr. Noah Khalil",      "department": "engineering",  "role_file": "ROLE__Noah-Khalil__v02.md"},
    {"agt_id": "AGT-011", "callsign": "MAESTRA",  "name": "Maia Kline",           "department": "engineering",  "role_file": "ROLE__Maestra-Kline__v02.md"},
    {"agt_id": "AGT-012", "callsign": "AXIS",     "name": "Alex Harris",          "department": "delivery",     "role_file": "ROLE__Alex-Harris__v02.md"},
    {"agt_id": "AGT-013", "callsign": "BRIDGE",   "name": "Maya Torres",          "department": "delivery",     "role_file": "ROLE__Maya-Torres__v02.md"},
    {"agt_id": "AGT-014", "callsign": "CLOSE",    "name": "Jordan Reese",         "department": "sales",        "role_file": "ROLE__Jordan-Reese__v02.md"},
    {"agt_id": "AGT-015", "callsign": "SPARK",    "name": "Taylor Morgan",        "department": "sales",        "role_file": "ROLE__Taylor-Morgan__v02.md"},
    {"agt_id": "AGT-016", "callsign": "CIPH",     "name": "Cipher Little",        "department": "digital",      "role_file": "ROLE__Cipher-Little__v02.md"},
    {"agt_id": "AGT-017", "callsign": "SCOPE",    "name": "Clyde Nevestein",      "department": "intelligence", "role_file": "ROLE__Clyde-Nevestein__v02.md"},
]

# Department → Redis channel mapping
DEPARTMENT_CHANNELS: dict[str, str] = {
    "hq":           "dept:hq",
    "strategy":     "dept:strategy",
    "governance":   "dept:governance",
    "finance":      "dept:finance",
    "engineering":  "dept:engineering",
    "security":     "dept:security",
    "delivery":     "dept:delivery",
    "sales":        "dept:sales",
    "digital":      "dept:digital",
    "intelligence": "dept:intelligence",
}


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — cached after first load."""
    return Settings()
