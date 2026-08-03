"""``audit_logs`` model (DATABASE_DESIGN.md §24).

Append-only security and compliance trail for privileged actions, destructive
operations, auth events, and knowledge base changes. Rows are never edited.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.types import IPAddress, JsonB

if TYPE_CHECKING:
    from app.models.users import User


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only security/compliance audit trail (DATABASE_DESIGN.md §24)."""

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JsonB, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JsonB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(IPAddress, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    __table_args__ = (
        sa.Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        sa.Index("ix_audit_logs_created_at", sa.text("created_at DESC")),
        sa.Index("ix_audit_logs_actor", "actor_user_id"),
    )

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])
