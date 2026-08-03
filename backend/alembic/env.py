"""Alembic migration environment (DATABASE_DESIGN.md §27).

Pulls ``sqlalchemy.url`` from the application settings (matching the runtime
database) and drives migrations against the async engine.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (registers every model with Base.metadata)
from app.config.settings import get_settings
from app.database.base import Base
from app.database.session import normalize_database_url
from app.database.utils import is_sqlite

config = context.config

settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    normalize_database_url(settings.database_url),
)

target_metadata = Base.metadata

# SQLite has no native ALTER support; batch mode is required for additive
# migrations in development (DATABASE_DESIGN.md §28 environment parity).
_USE_BATCH_MODE = is_sqlite(config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_USE_BATCH_MODE,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations against a live synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=_USE_BATCH_MODE,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations through the configured async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
