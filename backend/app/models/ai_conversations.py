"""``ai_conversations`` model (DATABASE_DESIGN.md §15).

AI & Knowledge: a chat session between a student and the multi-agent system.
Maps to the ``/chat/[conversationId]`` UI concept.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import AGENT_KEY, CONVERSATION_STATUS, AgentKey, ConversationStatus
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.chat_history import ChatMessage
    from app.models.departments import Department
    from app.models.requests import Request
    from app.models.users import User


class AIConversation(BaseModel, Base):
    """A chat session owned by a user (DATABASE_DESIGN.md §15)."""

    __tablename__ = "ai_conversations"

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
    title: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[ConversationStatus] = mapped_column(
        CONVERSATION_STATUS, nullable=False, server_default=sa.text("'active'")
    )
    current_agent: Mapped[AgentKey | None] = mapped_column(AGENT_KEY, nullable=True)
    message_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    total_tokens: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )

    __table_args__ = (
        sa.Index(
            "ix_ai_conversations_user_id_last_message",
            "user_id",
            sa.text("last_message_at DESC"),
        ),
        sa.Index("ix_ai_conversations_department_id", "department_id"),
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id], overlaps="conversations")
    department: Mapped[Department | None] = relationship(
        foreign_keys=[department_id], overlaps="conversations"
    )
    messages: Mapped[list[ChatMessage]] = relationship(
        passive_deletes=True, overlaps="conversation"
    )
    escalated_requests: Mapped[list[Request]] = relationship(
        foreign_keys="Request.conversation_id", overlaps="conversation"
    )
