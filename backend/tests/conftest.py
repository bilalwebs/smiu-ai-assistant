"""Shared test fixtures and environment setup (TESTING_STRATEGY.md §27).

Environment:
    Forces ``ENVIRONMENT=testing`` before the app is imported so every test
    runs against ``TestingSettings`` (in-memory SQLite, no ``.env`` file), and
    resets the settings/engine caches between tests.

Database fixtures:
    - ``db_engine``: a shared in-memory async engine with all ``Base`` tables
      created, for persistence-layer unit tests.
    - ``db_session``: a request-like ``AsyncSession`` bound to ``db_engine``.
    - ``connection``: a synchronous in-memory connection for migration/introspection
      helpers.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "testing"

from app.config.settings import clear_settings_cache
from app.core.app_factory import create_app
from app.database.base import Base
from app.database.session import reset_engine


@pytest.fixture()
def client() -> object:
    """Yield a TestClient with lifespan running and caches reset on teardown."""
    clear_settings_cache()
    reset_engine()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    clear_settings_cache()
    reset_engine()


@pytest.fixture()
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Yield an in-memory async engine with the full schema created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` bound to the shared in-memory engine."""
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


@pytest.fixture()
def connection() -> Iterator[Connection]:
    """Yield a synchronous in-memory connection with a sample schema.

    Used by the migration-helper tests, which introspect the schema rather
    than exercising the async engine.
    """
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
        )
        conn.execute(
            text("CREATE INDEX ix_test ON alembic_version (version_num)")
        )
        conn.commit()
        yield conn
    engine.dispose()
