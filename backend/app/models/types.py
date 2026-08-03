"""Dialect-safe column types (DATABASE_DESIGN.md §6.1, §28).

Purpose:
    PostgreSQL types that have no SQLite equivalent are wrapped so development
    (SQLite) and production (PostgreSQL) share one model layer: JSONB degrades
    to JSON on SQLite, and the ``inet`` type degrades to ``varchar(45)``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import TypeDecorator


class JsonB(TypeDecorator[Any]):
    """JSONB on PostgreSQL, plain JSON on SQLite (dev parity, §28)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


IPAddress = INET().with_variant(String(45), "sqlite")
