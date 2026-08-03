"""Migration helper tests (DATABASE_DESIGN.md §28).

Verifies the Alembic introspection helpers used by guarded revisions behave
idempotently against a live schema.
"""

from __future__ import annotations

from sqlalchemy.engine import Connection

from app.database.migration_helpers import column_exists, index_exists, table_exists


def test_table_exists(connection: Connection) -> None:
    assert table_exists(connection, "alembic_version") is True
    assert table_exists(connection, "does_not_exist") is False


def test_column_exists(connection: Connection) -> None:
    assert column_exists(connection, "alembic_version", "version_num") is True
    assert column_exists(connection, "alembic_version", "missing") is False
    assert column_exists(connection, "missing_table", "version_num") is False


def test_index_exists(connection: Connection) -> None:
    assert index_exists(connection, "alembic_version", "ix_test") is True
    assert index_exists(connection, "alembic_version", "ix_missing") is False
    assert index_exists(connection, "missing_table", "ix_test") is False
