"""Declarative base for all ORM models.

Purpose:
    Single SQLAlchemy 2.0 declarative base shared by every model
    (DATABASE_DESIGN.md §27; BACKEND_ARCHITECTURE.md §11).

Responsibilities:
    - Declare the base class and naming convention for constraints/indexes.
    - Provide the ``metadata`` consumed by Alembic autogenerate.

Usage:
    ``class User(Base): ...`` — imported from :mod:`app.database.base`.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with a consistent naming convention."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
