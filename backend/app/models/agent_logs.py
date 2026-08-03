"""``agent_logs`` model (DATABASE_DESIGN.md §4.3/§8.2/§9.2/§10.3; AI_ARCHITECTURE.md §11.2, §30.1).

Append-only agent routing/execution log. Persists the routing signal (intent,
selected agent, confidence), retrieval/grounding evidence, model/token/latency
usage, and error/retry/fallback outcomes for every run.

Note:
    The design catalogs the ``agent_logs`` FK set, indexes, and confidence check
    but does not give this table a dedicated column section; the column set
    below is assembled from those catalogs and the AI_ARCHITECTURE contract.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    AGENT_KEY,
    AGENT_RUN_STATUS,
    AgentKey,
    AgentRunStatus,
)
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.types import JsonB

if TYPE_CHECKING:
    from app.models.ai_conversations import AIConversation
    from app.models.chat_history import ChatMessage
    from app.models.users import User


class AgentLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only agent routing/execution log (DATABASE_DESIGN.md §24 note)."""

    __tablename__ = "agent_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_key: Mapped[AgentKey | None] = mapped_column(AGENT_KEY, nullable=True)
    intent: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    run_status: Mapped[AgentRunStatus] = mapped_column(AGENT_RUN_STATUS, nullable=False)
    confidence: Mapped[float | None] = mapped_column(sa.Numeric(4, 3), nullable=True)
    model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JsonB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    retry_count: Mapped[int | None] = mapped_column(
        sa.SmallInteger, nullable=True, server_default=sa.text("0")
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JsonB, nullable=True, server_default=sa.text("'{}'")
    )

    __table_args__ = (
        sa.Index("ix_agent_logs_conversation_id", "conversation_id"),
        sa.Index("ix_agent_logs_created_at", sa.text("created_at DESC")),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_check",
        ),
    )

    user: Mapped[User | None] = relationship(foreign_keys=[user_id], overlaps="agent_logs")
    conversation: Mapped[AIConversation | None] = relationship(
        foreign_keys=[conversation_id]
    )
    message: Mapped[ChatMessage | None] = relationship(
        foreign_keys=[message_id], overlaps="agent_logs"
    )
