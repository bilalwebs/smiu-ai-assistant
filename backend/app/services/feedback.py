"""``feedback`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §23).

Workflow & Support: user ratings, comments, and flags on AI messages. The
service enforces the rating 1-5 and rating-type-only rules from the schema
constraints, the one-feedback-per-type-per-message idempotency rule
(API_SPECIFICATION.md §34.2), and the triage state machine (DATABASE_DESIGN.md §23).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Feedback,
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
)
from app.repositories import (
    ChatMessageRepository,
    ConversationRepository,
    FeedbackRepository,
    UserRepository,
)
from app.services.base import BaseService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)

_ALLOWED_TRANSITIONS: dict[FeedbackStatus, frozenset[FeedbackStatus]] = {
    FeedbackStatus.OPEN: frozenset(
        {
            FeedbackStatus.ACKNOWLEDGED,
            FeedbackStatus.RESOLVED,
            FeedbackStatus.DISMISSED,
        }
    ),
    FeedbackStatus.ACKNOWLEDGED: frozenset(
        {FeedbackStatus.RESOLVED, FeedbackStatus.DISMISSED}
    ),
    FeedbackStatus.RESOLVED: frozenset(),
    FeedbackStatus.DISMISSED: frozenset(),
}


class FeedbackService(BaseService):
    """Feedback operations for :class:`app.models.feedback.Feedback`."""

    def __init__(
        self,
        session: AsyncSession,
        feedback: FeedbackRepository | None = None,
        users: UserRepository | None = None,
        messages: ChatMessageRepository | None = None,
        conversations: ConversationRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._feedback = feedback or FeedbackRepository(session)
        self._users = users or UserRepository(session)
        self._messages = messages or ChatMessageRepository(session)
        self._conversations = conversations or ConversationRepository(session)

    async def submit_feedback(
        self,
        *,
        user_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        feedback_type: FeedbackType = FeedbackType.RATING,
        rating: int | None = None,
        comment: str | None = None,
        sentiment: FeedbackSentiment | None = None,
        status: FeedbackStatus = FeedbackStatus.OPEN,
        resolution_notes: str | None = None,
    ) -> Feedback:
        """Submit a rating/comment/flag on an AI message (API_SPECIFICATION.md §21.5)."""
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError(message="User not found")
        if message_id is not None and await self._messages.get_by_id(message_id) is None:
            raise NotFoundError(message="Message not found")
        if (
            conversation_id is not None
            and await self._conversations.get_by_id(conversation_id) is None
        ):
            raise NotFoundError(message="Conversation not found")
        feedback_type = self._validate_enum(feedback_type, FeedbackType, field="feedback_type")
        status = self._validate_enum(status, FeedbackStatus, field="status")
        sentiment = (
            self._validate_enum(sentiment, FeedbackSentiment, field="sentiment")
            if sentiment is not None
            else None
        )
        self._validate_rating(feedback_type, rating)
        if message_id is not None:
            existing = await self._feedback.get(
                Feedback.user_id == user_id,
                Feedback.message_id == message_id,
                Feedback.feedback_type == feedback_type,
            )
            if existing is not None:
                raise ConflictError(
                    message="Feedback of this type already exists for this message",
                    details=[
                        {"field": "message_id", "reason": "feedback already submitted"},
                        {"field": "feedback_type", "reason": "already submitted"},
                    ],
                )
        return await self._feedback.create(
            user_id=user_id,
            message_id=message_id,
            conversation_id=conversation_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            sentiment=sentiment,
            status=status,
            resolution_notes=resolution_notes,
        )

    async def update_status(
        self,
        *,
        feedback_id: uuid.UUID,
        status: FeedbackStatus,
        resolution_notes: str | None = None,
    ) -> Feedback:
        """Transition feedback through the triage state machine."""
        feedback = await self._require_feedback(feedback_id)
        status = self._validate_enum(status, FeedbackStatus, field="status")
        if status == feedback.status:
            raise InvalidStateError(
                message=f"Feedback is already {feedback.status.value}",
                details=[{"field": "status", "reason": "no state change"}],
            )
        allowed = _ALLOWED_TRANSITIONS.get(feedback.status, frozenset())
        if status not in allowed:
            raise InvalidStateError(
                message=(
                    f"Cannot transition feedback from {feedback.status.value} "
                    f"to {status.value}"
                ),
                details=[{"field": "status", "reason": "invalid transition"}],
            )
        changes: dict[str, Any] = {"status": status}
        if status == FeedbackStatus.RESOLVED and resolution_notes is not None:
            changes["resolution_notes"] = resolution_notes
        return await self._feedback.update(feedback, **changes)

    async def delete_feedback(self, *, feedback_id: uuid.UUID) -> Feedback:
        """Soft-delete feedback (DATABASE_DESIGN.md §26)."""
        feedback = await self._require_feedback(feedback_id)
        return await self._feedback.soft_delete(feedback)

    @staticmethod
    def _validate_rating(feedback_type: FeedbackType, rating: int | None) -> None:
        """Enforce the rating range and rating-only rules from the constraints."""
        if feedback_type == FeedbackType.RATING:
            if rating is None:
                raise ValidationError(
                    message="rating is required for rating feedback",
                    details=[{"field": "rating", "reason": "required"}],
                )
            if not 1 <= rating <= 5:
                raise ValidationError(
                    message="rating must be between 1 and 5",
                    details=[{"field": "rating", "reason": "out of range"}],
                )
        elif rating is not None:
            raise ValidationError(
                message="rating is only allowed for rating feedback",
                details=[{"field": "rating", "reason": "not allowed for this type"}],
            )

    async def _require_feedback(self, feedback_id: uuid.UUID) -> Feedback:
        feedback = await self._feedback.get_by_id(feedback_id)
        if feedback is None:
            raise NotFoundError(message="Feedback not found")
        return feedback
