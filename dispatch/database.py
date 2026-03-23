"""
SYSTVETAM — Database Layer
Zentraux Group LLC

Async SQLAlchemy 2.0 with asyncpg driver.
PostgreSQL is the persistence layer for the entire Systvetam.
State machine constraints enforced at the DB level — not application code.

Connection: DATABASE_URL from config (postgresql+asyncpg://)
"""

from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from dispatch.config import settings

# ---------------------------------------------------------------------------
# Naming convention — Alembic auto-generates clean migration names
# ---------------------------------------------------------------------------

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# ---------------------------------------------------------------------------
# Declarative Base — all ORM models inherit from this
# ---------------------------------------------------------------------------

class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all Systvetam ORM models.
    AsyncAttrs enables lazy-loading on async sessions.
    """
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---------------------------------------------------------------------------
# Engine — single async engine, connection pooled
# ---------------------------------------------------------------------------

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)


# ---------------------------------------------------------------------------
# Session factory — produces AsyncSession instances
# ---------------------------------------------------------------------------

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency — inject into route handlers
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async DB session scoped to a single request.
    Commits on success, rolls back on exception.

    Usage:
        @router.get("/tasks")
        async def list_tasks(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
