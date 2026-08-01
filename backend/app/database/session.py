"""Async engine and session factory.

Purpose:
    Create and expose the SQLAlchemy async engine and session factory
    (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §27).

Responsibilities:
    - Build engines lazily, one per database URL, from settings.
    - Map ``sqlite+aiosqlite`` URLs onto a shared in-memory pool (tests) with
      ``StaticPool``; production uses the configured PostgreSQL URL and pool.
    - Expose ``get_session_factory`` for request-scoped sessions.
    - Provide ``reset_engine`` so tests can rebuild after settings changes.

Usage:
    ``get_session_factory()`` is consumed by
    :func:`app.dependencies.database.get_db_session`.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings, get_settings

_engines: dict[str, AsyncEngine] = {}
_sessionmakers: dict[str, async_sessionmaker[AsyncSession]] = {}


def _is_sqlite(database_url: str) -> bool:
    return make_url(database_url).get_backend_name() == "sqlite"


def normalize_database_url(database_url: str) -> str:
    """Return a URL the async engine can drive.

    PostgreSQL is accessed through the async ``asyncpg`` driver, so sync
    ``postgresql://`` / ``postgresql+psycopg://`` URLs (e.g. the copy-paste
    URLs from Neon) are rewritten to ``postgresql+asyncpg://`` and libpq-only
    query parameters (``sslmode``, ``channel_binding``) are translated to
    their asyncpg equivalents (``ssl``).
    """
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or url.drivername == "postgresql+asyncpg":
        return database_url
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode is not None and sslmode != "disable" and "ssl" not in query:
        query["ssl"] = sslmode
    return url.set(drivername="postgresql+asyncpg", query=query).render_as_string(
        hide_password=False
    )


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the async engine for the active settings, creating it on first use."""
    active = settings or get_settings()
    database_url = normalize_database_url(active.database_url)
    engine = _engines.get(database_url)
    if engine is None:
        if _is_sqlite(database_url):
            kwargs: dict[str, object] = {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            }
        else:
            kwargs = {
                "pool_size": active.db_pool_size,
                "max_overflow": active.db_max_overflow,
                "pool_timeout": active.db_pool_timeout,
                "pool_recycle": active.db_pool_recycle,
            }
        engine = create_async_engine(database_url, **kwargs)
        _engines[database_url] = engine
    return engine


def get_session_factory(
    settings: Settings | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return a cached async session factory bound to the active engine."""
    active = settings or get_settings()
    database_url = normalize_database_url(active.database_url)
    factory = _sessionmakers.get(database_url)
    if factory is None:
        factory = async_sessionmaker(
            bind=get_engine(active),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        _sessionmakers[database_url] = factory
    return factory


def reset_engine() -> None:
    """Dispose and clear cached engines (used by tests)."""
    for url, engine in list(_engines.items()):
        _dispose(engine)
        _engines.pop(url, None)
    _sessionmakers.clear()


def _dispose(engine: AsyncEngine) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        loop.create_task(engine.dispose())
    else:
        asyncio.run(engine.dispose())
