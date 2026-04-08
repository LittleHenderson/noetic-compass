"""Database connection management -- async SQLAlchemy engine + session factory.

Only initialised when NC_DATABASE_URL is set.  Otherwise all functions are
no-ops and the application falls back to the in-memory store.
"""

from __future__ import annotations

from typing import Any

try:
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    _HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover
    _HAS_SQLALCHEMY = False

    # Provide type stubs so the module still loads
    AsyncEngine = Any  # type: ignore[assignment,misc]
    AsyncSession = Any  # type: ignore[assignment,misc]
    async_sessionmaker = None  # type: ignore[assignment,misc]
    create_async_engine = None  # type: ignore[assignment]

from api.config import settings

# Module-level singletons -- lazily created by ``init_db``.
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None  # type: ignore[assignment]


async def init_db() -> None:
    """Create the async engine and session factory, then run migrations.

    Safe to call when DATABASE_URL is unset or SQLAlchemy is not installed
    -- becomes a no-op.
    """
    global engine, async_session_factory

    if not settings.database_url:
        return

    if not _HAS_SQLALCHEMY:  # pragma: no cover
        import warnings

        warnings.warn(
            "NC_DATABASE_URL is set but sqlalchemy[asyncio] is not installed. "
            "Falling back to in-memory store.",
            stacklevel=2,
        )
        return

    engine = create_async_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Run table creation
    from api.models_db import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None


async def check_db() -> bool:
    """Return True if the database connection is healthy."""
    if engine is None:
        return False
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
