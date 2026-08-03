"""full application schema

Chains the complete Phase 2B schema (all 16 tables per DATABASE_DESIGN.md §5)
from the Phase 2A baseline. Per §28 ("baseline generates all tables from the
models") the tables, constraints, and indexes are created from the ORM
metadata so the migration is identical to the models by construction; on
PostgreSQL the shared enum types are emitted by the model schema events, and
on SQLite the portable variants (JSONB -> JSON, inet -> varchar, enum ->
varchar) apply automatically.

Revision ID: 2c3d4e5f6a7b
Revises: 1a2b3c4d5e6f
Create Date: 2026-08-03 12:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

import app.models  # noqa: F401  (registers every model with Base.metadata)
from app.database.base import Base

revision: str = "2c3d4e5f6a7b"
down_revision: str | None = "1a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all 16 tables plus their constraints and indexes."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop all 16 tables (PostgreSQL enum types drop with them)."""
    Base.metadata.drop_all(bind=op.get_bind())
