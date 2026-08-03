"""``users`` model (DATABASE_DESIGN.md §12).

Identity & Access: every account (student, admin, future faculty) with its
authentication identity, role, and lifecycle columns.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import USER_ROLE, USER_STATUS, UserRole, UserStatus
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.agent_logs import AgentLog
    from app.models.ai_conversations import AIConversation
    from app.models.audit_logs import AuditLog
    from app.models.documents import Document
    from app.models.feedback import Feedback
    from app.models.notifications import Notification
    from app.models.requests import Request
    from app.models.sessions import UserSession
    from app.models.students import Student


class User(BaseModel, Base):
    """A platform account (DATABASE_DESIGN.md §12)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        USER_ROLE, nullable=False, server_default=sa.text("'student'")
    )
    status: Mapped[UserStatus] = mapped_column(
        USER_STATUS, nullable=False, server_default=sa.text("'pending'")
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        sa.SmallInteger, nullable=False, server_default=sa.text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JsonB, nullable=True, server_default=sa.text("'{}'")
    )
    locale: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, server_default=sa.text("'en'")
    )

    __table_args__ = (
        sa.Index("ix_users_email_key", "email", unique=True),
        sa.Index("ix_users_role", "role"),
        sa.Index("ix_users_status", "status"),
    )

    student: Mapped[Student | None] = relationship(
        uselist=False, passive_deletes=True, overlaps="user"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        passive_deletes=True, overlaps="user"
    )
    conversations: Mapped[list[AIConversation]] = relationship(
        passive_deletes=True, overlaps="user"
    )
    owned_requests: Mapped[list[Request]] = relationship(
        foreign_keys="Request.user_id", passive_deletes=True, overlaps="owner"
    )
    assigned_requests: Mapped[list[Request]] = relationship(
        foreign_keys="Request.assigned_to", overlaps="assignee"
    )
    notifications: Mapped[list[Notification]] = relationship(
        passive_deletes=True, overlaps="user"
    )
    feedback: Mapped[list[Feedback]] = relationship(
        passive_deletes=True, overlaps="user"
    )
    documents: Mapped[list[Document]] = relationship(
        foreign_keys="Document.user_id", overlaps="user"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        foreign_keys="AuditLog.actor_user_id", overlaps="actor"
    )
    agent_logs: Mapped[list[AgentLog]] = relationship(
        foreign_keys="AgentLog.user_id", overlaps="user"
    )
