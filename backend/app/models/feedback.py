"""``feedback`` model (DATABASE_DESIGN.md §23).

Workflow & Support: user ratings, comments, and flags on AI messages.
Supports the thumbs-up/down UI and model quality evaluation.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import BaseModel
from app.models.enums import (
    FEEDBACK_SENTIMENT,
    FEEDBACK_STATUS,
    FEEDBACK_TYPE,
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
)

if TYPE_CHECKING:
    from app.models.ai_conversations import AIConversation
    from app.models.chat_history import ChatMessage
    from app.models.users import User


class Feedback(BaseModel, Base):
    """Rating / comment / flag on an AI message (DATABASE_DESIGN.md §23)."""

    __tablename__ = "feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(
        FEEDBACK_TYPE, nullable=False, server_default=sa.text("'rating'")
    )
    rating: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    comment: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    sentiment: Mapped[FeedbackSentiment | None] = mapped_column(
        FEEDBACK_SENTIMENT, nullable=True
    )
    status: Mapped[FeedbackStatus] = mapped_column(
        FEEDBACK_STATUS, nullable=False, server_default=sa.text("'open'")
    )
    resolution_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.Index("ix_feedback_user_id", "user_id"),
        sa.Index("ix_feedback_message_id", "message_id"),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)", name="rating_check"
        ),
        sa.CheckConstraint(
            "feedback_type = 'rating' OR rating IS NULL", name="rating_type_check"
        ),
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id], overlaps="feedback")
    message: Mapped[ChatMessage | None] = relationship(
        foreign_keys=[message_id], overlaps="feedback"
    )
    conversation: Mapped[AIConversation | None] = relationship(
        foreign_keys=[conversation_id]
    )
