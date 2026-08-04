"""``feedback`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import (
    FeedbackSentiment,
    FeedbackStatus,
    FeedbackType,
    MessageRole,
)
from app.services import FeedbackService
from app.services.exceptions import ConflictError, InvalidStateError, NotFoundError, ValidationError


async def _message(conversation_service, chat_history_service, user_factory):
    user = await user_factory()
    conversation = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="Here are the admission deadlines.",
    )
    return user, message


async def test_submit_rating_happy_path(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.RATING,
        rating=5,
    )
    assert feedback.feedback_type == FeedbackType.RATING
    assert feedback.rating == 5
    assert feedback.status == FeedbackStatus.OPEN


async def test_submit_comment_without_rating(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.COMMENT,
        comment="Please add deadlines for spring intake.",
        sentiment=FeedbackSentiment.NEUTRAL,
    )
    assert feedback.comment == "Please add deadlines for spring intake."
    assert feedback.rating is None


async def test_submit_flag(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.FLAG,
        comment="Incorrect deadline shown.",
    )
    assert feedback.feedback_type == FeedbackType.FLAG


async def test_submit_rating_required_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(ValidationError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            message_id=message.id,
            feedback_type=FeedbackType.RATING,
        )


async def test_submit_rating_out_of_range_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(ValidationError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            message_id=message.id,
            feedback_type=FeedbackType.RATING,
            rating=6,
        )


async def test_submit_rating_on_comment_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(ValidationError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            message_id=message.id,
            feedback_type=FeedbackType.COMMENT,
            rating=4,
        )


async def test_submit_duplicate_type_for_message_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.RATING,
        rating=4,
    )
    with pytest.raises(ConflictError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            message_id=message.id,
            feedback_type=FeedbackType.RATING,
            rating=5,
        )


async def test_submit_comment_and_rating_distinct(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.RATING,
        rating=4,
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id,
        message_id=message.id,
        feedback_type=FeedbackType.COMMENT,
        comment="Add fall deadlines.",
    )
    assert feedback.feedback_type == FeedbackType.COMMENT


async def test_submit_missing_user_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    _, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(NotFoundError):
        await feedback_service.submit_feedback(
            user_id=uuid.uuid4(),
            message_id=message.id,
            feedback_type=FeedbackType.RATING,
            rating=3,
        )


async def test_submit_missing_message_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, _ = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(NotFoundError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            message_id=uuid.uuid4(),
            feedback_type=FeedbackType.RATING,
            rating=3,
        )


async def test_submit_missing_conversation_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, _ = await _message(
        conversation_service, chat_history_service, user_factory
    )
    with pytest.raises(NotFoundError):
        await feedback_service.submit_feedback(
            user_id=user.id,
            conversation_id=uuid.uuid4(),
            feedback_type=FeedbackType.COMMENT,
            comment="Hello",
        )


async def test_update_status_acknowledges_then_resolves(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id, message_id=message.id, feedback_type=FeedbackType.FLAG
    )
    acknowledged = await feedback_service.update_status(
        feedback_id=feedback.id, status=FeedbackStatus.ACKNOWLEDGED
    )
    assert acknowledged.status == FeedbackStatus.ACKNOWLEDGED
    resolved = await feedback_service.update_status(
        feedback_id=feedback.id,
        status=FeedbackStatus.RESOLVED,
        resolution_notes="Fixed the source document.",
    )
    assert resolved.status == FeedbackStatus.RESOLVED
    assert resolved.resolution_notes == "Fixed the source document."


async def test_update_status_same_status_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id, message_id=message.id, feedback_type=FeedbackType.FLAG
    )
    with pytest.raises(InvalidStateError):
        await feedback_service.update_status(
            feedback_id=feedback.id, status=FeedbackStatus.OPEN
        )


async def test_update_status_invalid_transition_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id, message_id=message.id, feedback_type=FeedbackType.FLAG
    )
    await feedback_service.update_status(
        feedback_id=feedback.id, status=FeedbackStatus.RESOLVED
    )
    with pytest.raises(InvalidStateError):
        await feedback_service.update_status(
            feedback_id=feedback.id, status=FeedbackStatus.OPEN
        )


async def test_update_status_invalid_enum_raises(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id, message_id=message.id, feedback_type=FeedbackType.FLAG
    )
    with pytest.raises(ValidationError):
        await feedback_service.update_status(
            feedback_id=feedback.id, status="bogus"
        )


async def test_delete_feedback_soft_deletes(
    conversation_service, chat_history_service, feedback_service, user_factory
) -> None:
    user, message = await _message(
        conversation_service, chat_history_service, user_factory
    )
    feedback = await feedback_service.submit_feedback(
        user_id=user.id, message_id=message.id, feedback_type=FeedbackType.RATING, rating=4
    )
    deleted = await feedback_service.delete_feedback(feedback_id=feedback.id)
    assert deleted.is_deleted


async def test_missing_feedback_raises(
    feedback_service: FeedbackService,
) -> None:
    with pytest.raises(NotFoundError):
        await feedback_service.update_status(
            feedback_id=uuid.uuid4(), status=FeedbackStatus.RESOLVED
        )
