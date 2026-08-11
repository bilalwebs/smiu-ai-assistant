"""seed departments

Phase 1 department rows per DATABASE_DESIGN.md §14 and §32.3: the three
routing targets (Admission Office, Examination Department, Student Support
Office) plus the Computer Science academic reference row. Routing is
data-driven, so new departments are added as data, never code; this revision
makes the baseline departments present on every database (Neon PostgreSQL in
development, SQLite in the local test profile).

The insert is idempotent (keyed on the unique ``code``) and dialect-safe: a
per-row existence guard works identically on PostgreSQL and SQLite, unlike
``ON CONFLICT``/``INSERT OR IGNORE`` which differ per dialect. Rows carry
fixed, deterministic UUIDs so the seeded identities are stable across
environments and can be referenced by seed-aware tests and integrations.

Revision ID: 4e5f6a7b8c9d
Revises: 3d4e5f6a7b8c
Create Date: 2026-08-07 00:00:00

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.enums import AGENT_KEY

revision: str = "4e5f6a7b8c9d"
down_revision: str | None = "3d4e5f6a7b8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Phase 1 departments (DATABASE_DESIGN.md §14, §32.3). Fixed UUIDs keep the
#: seeded identities stable so registration can reference them deterministically.
_DEPARTMENTS: list[dict[str, object]] = [
    {
        "id": "10000000-0000-4000-8000-000000000001",
        "code": "ADM",
        "name": "Admission Office",
        "agent_key": "admission",
        "is_active": True,
        "sort_order": 0,
    },
    {
        "id": "10000000-0000-4000-8000-000000000002",
        "code": "EXM",
        "name": "Examination Department",
        "agent_key": "examination",
        "is_active": True,
        "sort_order": 1,
    },
    {
        "id": "10000000-0000-4000-8000-000000000003",
        "code": "SSO",
        "name": "Student Support Office",
        "agent_key": "faq",
        "is_active": True,
        "sort_order": 2,
    },
    {
        "id": "10000000-0000-4000-8000-000000000004",
        "code": "CS",
        "name": "Computer Science Department",
        "agent_key": None,
        "is_active": True,
        "sort_order": 3,
    },
]


def upgrade() -> None:
    """Insert the Phase 1 departments when absent (idempotent by ``code``)."""
    bind = op.get_bind()
    departments = sa.table(
        "departments",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String(20)),
        sa.column("name", sa.String(150)),
        sa.column("agent_key", AGENT_KEY),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.SmallInteger()),
    )
    for row in _DEPARTMENTS:
        exists = bind.execute(
            sa.select(departments.c.id)
            .where(departments.c.code == row["code"])
            .limit(1)
        ).first()
        if exists is None:
            values = {**row, "id": uuid.UUID(str(row["id"]))}
            bind.execute(departments.insert().values(**values))


def downgrade() -> None:
    """Remove the seeded departments by their unique codes."""
    bind = op.get_bind()
    departments = sa.table("departments", sa.column("code", sa.String(20)))
    bind.execute(
        departments.delete().where(
            departments.c.code.in_([row["code"] for row in _DEPARTMENTS])
        )
    )
