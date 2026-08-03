"""``chat_history`` model (DATABASE_DESIGN.md §16).

AI & Knowledge: one row per message in a conversation (PROJECT_RULES.md
``chat_history`` table). All message roles, streaming lifecycle states, and RAG
citations originate here.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import (
    AGENT_KEY,
    MESSAGE_ROLE,
    MESSAGE_STATUS,
    AgentKey,
    MessageRole,
    MessageStatus,
)
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.agent_logs import AgentLog
    from app.models.ai_conversations import AIConversation
    from app.models.ai_sources import AISource
    from app.models.documents import Document
    from app.models.feedback import Feedback


class ChatMessage(BaseModel, Base):
    """A single message within a conversation (DATABASE_DESIGN.md §16)."""

    __tablename__ = "chat_history"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[MessageRole] = mapped_column(MESSAGE_ROLE, nullable=False)
    agent_key: Mapped[AgentKey | None] = mapped_column(AGENT_KEY, nullable=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content_format: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default=sa.text("'markdown'")
    )
    status: Mapped[MessageStatus] = mapped_column(
        MESSAGE_STATUS, nullable=False, server_default=sa.text("'completed'")
    )
    model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(
        JsonB, nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )

    __table_args__ = (
        sa.Index(
            "ix_chat_history_conversation_id_created", "conversation_id", "created_at"
        ),
        sa.Index("ix_chat_history_parent_message_id", "parent_message_id"),
        sa.CheckConstraint(
            "(role IN ('user', 'system', 'tool') AND status IN ('completed', 'error'))"
            " OR role <> 'assistant'"
            " OR status IN ('queued', 'streaming', 'completed', 'stopped')",
            name="status_roles_check",
        ),
    )

    conversation: Mapped[AIConversation] = relationship(
        foreign_keys=[conversation_id], overlaps="messages"
    )
    parent_message: Mapped[ChatMessage | None] = relationship(
        remote_side="ChatMessage.id", foreign_keys=[parent_message_id]
    )
    replies: Mapped[list[ChatMessage]] = relationship(
        remote_side=[parent_message_id],
        foreign_keys=[parent_message_id],
        overlaps="parent_message",
    )
    ai_sources: Mapped[list[AISource]] = relationship(
        passive_deletes=True, overlaps="message"
    )
    feedback: Mapped[list[Feedback]] = relationship(overlaps="message")
    documents: Mapped[list[Document]] = relationship(overlaps="message")
    agent_logs: Mapped[list[AgentLog]] = relationship(overlaps="message")
