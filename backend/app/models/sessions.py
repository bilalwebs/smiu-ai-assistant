"""``sessions`` model (DATABASE_DESIGN.md §25).

Identity & Access (PROJECT_RULES.md ``sessions`` table): server-side
refresh-token sessions. Access tokens are stateless JWTs; refresh tokens are
persisted hashed only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.types import IPAddress

if TYPE_CHECKING:
    from app.models.users import User


class UserSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Refresh-token-backed auth session (DATABASE_DESIGN.md §25)."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    access_jti: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    device_name: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(IPAddress, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    replaced_by_session_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        sa.Index("ix_sessions_user_id", "user_id"),
        sa.Index("ix_sessions_refresh_token_hash_key", "refresh_token_hash", unique=True),
        sa.Index(
            "ix_sessions_active_partial",
            "user_id",
            postgresql_where=sa.text("revoked_at IS NULL"),
            sqlite_where=sa.text("revoked_at IS NULL"),
        ),
        sa.CheckConstraint("expires_at > created_at", name="expiry_check"),
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id], overlaps="sessions")
    replaced_by: Mapped[UserSession | None] = relationship(
        remote_side="UserSession.id", foreign_keys=[replaced_by_session_id]
    )
    successors: Mapped[list[UserSession]] = relationship(
        remote_side=[replaced_by_session_id],
        foreign_keys=[replaced_by_session_id],
        overlaps="replaced_by",
    )
