"""``requests`` model (DATABASE_DESIGN.md §17).

Workflow & Support: the core persistable unit of student workflow automation.
Lifecycle matches the standardized status model in ui-ux-design.md §17.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import (
    REQUEST_PRIORITY,
    REQUEST_SOURCE,
    REQUEST_STATUS,
    REQUEST_TYPE,
    RequestPriority,
    RequestSource,
    RequestStatus,
    RequestType,
)

if TYPE_CHECKING:
    from app.models.ai_conversations import AIConversation
    from app.models.departments import Department
    from app.models.documents import Document
    from app.models.notifications import Notification
    from app.models.request_timeline import RequestTimeline
    from app.models.users import User


class Request(BaseModel, Base):
    """A student workflow request (DATABASE_DESIGN.md §17)."""

    __tablename__ = "requests"

    request_no: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[RequestType] = mapped_column(REQUEST_TYPE, nullable=False)
    category: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    priority: Mapped[RequestPriority] = mapped_column(
        REQUEST_PRIORITY, nullable=False, server_default=sa.text("'medium'")
    )
    status: Mapped[RequestStatus] = mapped_column(
        REQUEST_STATUS, nullable=False, server_default=sa.text("'draft'")
    )
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source: Mapped[RequestSource] = mapped_column(
        REQUEST_SOURCE, nullable=False, server_default=sa.text("'manual'")
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.Index("ix_requests_request_no_key", "request_no", unique=True),
        sa.Index("ix_requests_user_id", "user_id"),
        sa.Index("ix_requests_department_id", "department_id"),
        sa.Index("ix_requests_status_created", "status", sa.text("created_at DESC")),
        sa.Index(
            "ix_requests_active_partial",
            "status",
            postgresql_where=sa.text(
                "status IN ('submitted', 'in_review', 'assigned', 'processing')"
                " AND deleted_at IS NULL"
            ),
            sqlite_where=sa.text(
                "status IN ('submitted', 'in_review', 'assigned', 'processing')"
                " AND deleted_at IS NULL"
            ),
        ),
        sa.Index("ix_requests_assigned_to", "assigned_to"),
        sa.CheckConstraint(
            "status <> 'resolved' OR resolved_at IS NOT NULL",
            name="resolved_state_check",
        ),
        sa.CheckConstraint(
            "status <> 'rejected' OR rejection_reason IS NOT NULL",
            name="rejected_state_check",
        ),
    )

    owner: Mapped[User] = relationship(foreign_keys=[user_id], overlaps="owned_requests")
    assignee: Mapped[User | None] = relationship(
        foreign_keys=[assigned_to], overlaps="assigned_requests"
    )
    department: Mapped[Department | None] = relationship(
        foreign_keys=[department_id], overlaps="requests"
    )
    conversation: Mapped[AIConversation | None] = relationship(
        foreign_keys=[conversation_id], overlaps="escalated_requests"
    )
    timeline: Mapped[list[RequestTimeline]] = relationship(
        passive_deletes=True, overlaps="request"
    )
    documents: Mapped[list[Document]] = relationship(overlaps="request")
    notifications: Mapped[list[Notification]] = relationship(overlaps="request")
