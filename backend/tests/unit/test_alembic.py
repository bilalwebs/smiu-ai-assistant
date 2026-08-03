"""Alembic baseline migration tests (DATABASE_DESIGN.md §28; TESTING_STRATEGY.md §7.5).

Verifies the Phase 2A baseline applies cleanly on an empty database, creates no
application tables, and downgrades back to base.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config
from app.config.settings import clear_settings_cache

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ALEMBIC_DIR = _BACKEND_DIR / "alembic"


@pytest.fixture()
def database_url_env() -> Iterator[None]:
    """Restore the previous ``DATABASE_URL`` and settings cache afterwards."""
    previous = os.environ.get("DATABASE_URL")
    yield
    clear_settings_cache()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


def _make_config(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    clear_settings_cache()
    config = Config(str(_BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(_ALEMBIC_DIR))
    config.set_main_option("prepend_sys_path", str(_BACKEND_DIR))
    return config


def _tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    engine.dispose()
    return tables


def _sync_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _async_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


_BASELINE_REVISION = "1a2b3c4d5e6f"

_CORE_TABLES = {
    "users",
    "students",
    "departments",
    "ai_conversations",
    "chat_history",
    "requests",
    "request_timeline",
    "notifications",
    "documents",
    "knowledge_documents",
    "knowledge_chunks",
    "ai_sources",
    "feedback",
    "audit_logs",
    "agent_logs",
    "sessions",
}


def test_baseline_upgrade_creates_only_version_table(database_url_env: None) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "baseline.db"
        command.upgrade(_make_config(_async_url(db_path)), _BASELINE_REVISION)
        assert _tables(_sync_url(db_path)) == {"alembic_version"}


def test_baseline_downgrade_is_reversible(database_url_env: None) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "baseline.db"
        config = _make_config(_async_url(db_path))
        command.upgrade(config, _BASELINE_REVISION)
        command.downgrade(config, "base")

        engine = create_engine(_sync_url(db_path))
        with engine.connect() as conn:
            version_count = conn.scalar(text("SELECT COUNT(*) FROM alembic_version"))
        engine.dispose()
        assert version_count == 0

        command.upgrade(config, _BASELINE_REVISION)
        assert _tables(_sync_url(db_path)) == {"alembic_version"}


def test_full_schema_upgrade_creates_all_tables(database_url_env: None) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "full.db"
        command.upgrade(_make_config(_async_url(db_path)), "head")
        assert _tables(_sync_url(db_path)) >= _CORE_TABLES


def test_full_schema_downgrade_is_reversible(database_url_env: None) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "full.db"
        config = _make_config(_async_url(db_path))
        command.upgrade(config, "head")
        assert _tables(_sync_url(db_path)) >= _CORE_TABLES

        command.downgrade(config, _BASELINE_REVISION)
        assert _tables(_sync_url(db_path)) == {"alembic_version"}
