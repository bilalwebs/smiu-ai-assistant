"""Database URL normalization tests (DATABASE_DESIGN.md §27).

Sync PostgreSQL URLs are rewritten to the async ``asyncpg`` driver so the
engine selection is robust to copy-paste provider URLs (e.g. Neon).
"""

from __future__ import annotations

from app.database.session import normalize_database_url


def test_sync_postgres_url_becomes_asyncpg() -> None:
    normalized = normalize_database_url("postgresql://u:p@host:5432/db")
    assert normalized == "postgresql+asyncpg://u:p@host:5432/db"


def test_psycopg_url_becomes_asyncpg() -> None:
    normalized = normalize_database_url("postgresql+psycopg://u:p@localhost:5432/db")
    assert normalized == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_libpq_params_translated_to_asyncpg() -> None:
    normalized = normalize_database_url(
        "postgresql://u:p@host/db?sslmode=require&channel_binding=require"
    )
    assert normalized == "postgresql+asyncpg://u:p@host/db?ssl=require"


def test_disable_sslmode_dropped() -> None:
    normalized = normalize_database_url("postgresql://u:p@host/db?sslmode=disable")
    assert normalized == "postgresql+asyncpg://u:p@host/db"


def test_asyncpg_url_unchanged() -> None:
    url = "postgresql+asyncpg://u:p@host:5432/db?ssl=require"
    assert normalize_database_url(url) == url


def test_sqlite_url_unchanged() -> None:
    url = "sqlite+aiosqlite:///./data/dev.db"
    assert normalize_database_url(url) == url
