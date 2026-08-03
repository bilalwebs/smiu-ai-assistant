"""initial database baseline

Phase 2A establishes the migration baseline only: there are no application
tables yet, so this revision creates nothing beyond the Alembic version table.
Phase 3 chains the full schema (all 16 tables per DATABASE_DESIGN.md §5) from
this head.

Revision ID: 1a2b3c4d5e6f
Revises:
Create Date: 2026-08-03 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create only the Alembic version table (managed by Alembic itself)."""
    pass


def downgrade() -> None:
    """Drop nothing; the baseline is a no-op."""
    pass
