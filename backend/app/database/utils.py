"""Database URL and dialect helpers (DATABASE_DESIGN.md §27).

Purpose:
    Provide pure helpers for inspecting database URLs so the session factory,
    Alembic environment, and health checks share one implementation instead of
    duplicating driver-string checks.
"""

from __future__ import annotations

from sqlalchemy.engine import make_url

from app.database.constants import POSTGRESQL_BACKEND, SQLITE_BACKEND


def get_database_backend(database_url: str) -> str:
    """Return the dialect backend name (e.g. ``sqlite``, ``postgresql``)."""
    return make_url(database_url).get_backend_name()


def is_sqlite(database_url: str) -> bool:
    """Return ``True`` when the URL targets a SQLite database."""
    return get_database_backend(database_url) == SQLITE_BACKEND


def is_postgresql(database_url: str) -> bool:
    """Return ``True`` when the URL targets a PostgreSQL database."""
    return get_database_backend(database_url) == POSTGRESQL_BACKEND
