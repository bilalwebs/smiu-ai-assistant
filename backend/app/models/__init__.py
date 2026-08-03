"""ORM model package (BACKEND_ARCHITECTURE.md §5.1).

Purpose:
    Home for SQLAlchemy 2.0 models and the reusable column mixins. Phase 2A
    ships the mixins and the combined ``BaseModel``; concrete business models
    (users, requests, conversations, ...) land in Phase 3.

Usage:
    ``from app.models import BaseModel`` or the individual mixins.
"""

from app.models.base import BaseModel
from app.models.mixins import (
    AuditMixin,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)

__all__ = [
    "AuditMixin",
    "BaseModel",
    "CreatedAtMixin",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "UpdatedAtMixin",
    "VersionMixin",
]
