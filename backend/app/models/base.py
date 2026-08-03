"""Combined standard column mixin (DATABASE_DESIGN.md §4.4).

Purpose:
    ``BaseModel`` composes the standard columns every mutable table carries —
    ``id``, ``created_at``, ``updated_at``, ``deleted_at``, ``version`` — so
    Phase 3 models declare ``class User(BaseModel, Base): ...`` and inherit the
    exact column set defined in DATABASE_DESIGN.md §4.4.

Notes:
    - Append-only tables compose ``UUIDPrimaryKeyMixin`` + ``CreatedAtMixin``.
    - Models needing actor tracking add ``AuditMixin`` explicitly.
"""

from __future__ import annotations

from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """Standard mutable-table column set (DATABASE_DESIGN.md §4.4)."""
