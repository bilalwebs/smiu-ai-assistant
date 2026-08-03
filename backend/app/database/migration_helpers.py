"""Migration helper utilities (DATABASE_DESIGN.md §28).

Purpose:
    Provide idempotent introspection helpers used inside Alembic revisions so
    guarded upgrades read clearly and behave identically across PostgreSQL and
    SQLite (the project's developer-parity databases).
"""

from __future__ import annotations

from sqlalchemy import Connection, inspect


def table_exists(connection: Connection, table_name: str) -> bool:
    """Return ``True`` when ``table_name`` exists in the current schema."""
    return inspect(connection).has_table(table_name)


def column_exists(connection: Connection, table_name: str, column_name: str) -> bool:
    """Return ``True`` when ``column_name`` exists on ``table_name``."""
    if not table_exists(connection, table_name):
        return False
    return column_name in {
        column["name"] for column in inspect(connection).get_columns(table_name)
    }


def index_exists(connection: Connection, table_name: str, index_name: str) -> bool:
    """Return ``True`` when ``index_name`` exists on ``table_name``."""
    if not table_exists(connection, table_name):
        return False
    return index_name in {
        index["name"] for index in inspect(connection).get_indexes(table_name)
    }
