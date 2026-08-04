"""password reset token columns

Adds the single-use password-reset token storage to ``users``
(DATABASE_DESIGN.md §12; API_SPECIFICATION.md §16). The reset token is
persisted only as its SHA-256 digest (matching ``sessions.refresh_token_hash``,
§25) plus an expiry timestamp, so a reset token can be invalidated once used.

The revision is guarded with ``column_exists`` so it applies identically on
databases created before this change and on databases whose full schema was
regenerated from the ORM models (where the columns already exist).

Revision ID: 3d4e5f6a7b8c
Revises: 2c3d4e5f6a7b
Create Date: 2026-08-04 12:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.database.migration_helpers import column_exists

revision: str = "3d4e5f6a7b8c"
down_revision: str | None = "2c3d4e5f6a7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS: list[tuple[str, sa.Column]] = [
    (
        "password_reset_token_hash",
        sa.Column("password_reset_token_hash", sa.String(64), nullable=True),
    ),
    (
        "password_reset_token_expires_at",
        sa.Column(
            "password_reset_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
]


def upgrade() -> None:
    """Add the two password-reset columns to ``users`` when absent."""
    with op.batch_alter_table("users") as batch_op:
        for name, column in _COLUMNS:
            if not column_exists(op.get_bind(), "users", name):
                batch_op.add_column(column)


def downgrade() -> None:
    """Drop the two password-reset columns from ``users``."""
    with op.batch_alter_table("users") as batch_op:
        for name, _ in _COLUMNS:
            if column_exists(op.get_bind(), "users", name):
                batch_op.drop_column(name)
