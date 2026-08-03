"""Reusable SQLAlchemy 2.0 column mixins (DATABASE_DESIGN.md §4.4, §7, §26).

Purpose:
    Provide the standard column set defined in DATABASE_DESIGN.md as composable
    mixins so every ORM model declares its persistence contract explicitly and
    never re-implements standard columns by hand.

Mixins:
    - ``UUIDPrimaryKeyMixin`` — ``id`` UUID primary key (immutable identity, §7).
    - ``CreatedAtMixin`` / ``UpdatedAtMixin`` / ``TimestampMixin`` — UTC
      timestamps with schema-level defaults (§4.4, §6.2).
    - ``SoftDeleteMixin`` — ``deleted_at`` marker plus lifecycle helpers (§26).
    - ``VersionMixin`` — optimistic-concurrency counter (§4.4, §34.5).
    - ``AuditMixin`` — optional actor identifiers (opt-in; FK wiring to
      ``users`` lands in Phase 3).

Usage:
    ``class User(BaseModel, Base): ...`` via :mod:`app.models.base`, or compose
    the individual mixins directly:
    ``class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base): ...``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.constants import DEFAULT_VERSION


class UUIDPrimaryKeyMixin:
    """Globally unique, immutable UUID primary key (DATABASE_DESIGN.md §7)."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class CreatedAtMixin:
    """``created_at`` — set once at insert time (UTC, schema-level default)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class UpdatedAtMixin:
    """``updated_at`` — refreshed on every write (UTC, schema-level default)."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin, UpdatedAtMixin):
    """Standard mutable-table timestamp pair (DATABASE_DESIGN.md §4.4)."""


class SoftDeleteMixin:
    """Soft-delete marker and lifecycle helpers (DATABASE_DESIGN.md §26).

    A row is "live" when ``deleted_at IS NULL``. Scoping queries to live rows
    is enforced by repositories (Phase 3), not by this mixin.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the row as deleted without removing it (§26)."""
        if not self.is_deleted:
            self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Clear the soft-delete marker, bringing the row back to live (§26)."""
        self.deleted_at = None


class VersionMixin:
    """Optimistic-concurrency counter (DATABASE_DESIGN.md §4.4, §34.5)."""

    version: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_VERSION,
        server_default=text(str(DEFAULT_VERSION)),
        nullable=False,
    )

    def increment_version(self) -> None:
        """Bump the version counter before a write (§34.5)."""
        self.version += 1


class AuditMixin:
    """Optional actor identifiers for sensitive rows.

    Nullable by design so the columns stay portable until Phase 3 wires real
    ``ForeignKey`` constraints to ``users.id`` on the models that opt in.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
