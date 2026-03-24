"""
SYSTVETAM — Alembic Environment Configuration
Zentraux Group LLC

Async migration runner for PostgreSQL via asyncpg.
All models imported to ensure Base.metadata is fully populated
before autogenerate or upgrade.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Alembic Config object — access to alembic.ini values
# ---------------------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so Base.metadata knows every table
# ---------------------------------------------------------------------------

from dispatch.models import crew_member, task, receipt  # noqa: F401
from dispatch.database import Base

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Database URL from environment — Railway injects DATABASE_URL at runtime
# ---------------------------------------------------------------------------


def _get_url() -> str:
    """
    Resolve the async database URL.
    Railway may provide postgresql:// — we enforce postgresql+asyncpg://.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. Cannot run migrations without a database."
        )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            "DATABASE_URL must use postgresql:// or postgresql+asyncpg:// scheme."
        )
    return url


# ---------------------------------------------------------------------------
# Offline mode — generates SQL script without connecting
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to stdout."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connects to live database via async engine
# ---------------------------------------------------------------------------


def do_run_migrations(connection) -> None:
    """Execute migrations within a synchronous connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to live database."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point — Alembic calls this
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
