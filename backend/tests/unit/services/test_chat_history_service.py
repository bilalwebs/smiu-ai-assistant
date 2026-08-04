"""``chat_history`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import AgentKey, MessageRole, MessageStatus
from app.services import ChatHistoryService
from app.services.exceptions import InvalidStateError, NotFoundError, ValidationError


async def test_add_message_happy_path(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conv.id, role=MessageRole.USER, content="Hi"
    )
    assert message.conversation_id == conv.id
    assert message.role == MessageRole.USER
    assert message.status == MessageStatus.COMPLETED


async def test_add_message_updates_conversation_counters(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    await chat_history_service.add_message(
        conversation_id=conv.id, role=MessageRole.USER, content="A"
    )
    await chat_history_service.add_message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="B",
        agent_key=AgentKey.ADMISSION,
        model="gpt-4o",
    )
    conv = await conversation_service.get_conversation(conversation_id=conv.id)
    assert conv.message_count == 2
    assert conv.last_message_at is not None


async def test_add_message_to_archived_conversation_raises(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    await conversation_service.archive_conversation(conversation_id=conv.id)
    with pytest.raises(InvalidStateError):
        await chat_history_service.add_message(
            conversation_id=conv.id, role=MessageRole.USER, content="Hi"
        )


async def test_add_message_missing_conversation_raises(
    chat_history_service: ChatHistoryService,
) -> None:
    with pytest.raises(NotFoundError):
        await chat_history_service.add_message(
            conversation_id=uuid.uuid4(), role=MessageRole.USER, content="Hi"
        )


async def test_add_message_blank_content_raises(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    with pytest.raises(ValidationError):
        await chat_history_service.add_message(
            conversation_id=conv.id, role=MessageRole.USER, content="  "
        )


async def test_add_message_invalid_role_status_raises(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    with pytest.raises(ValidationError):
        await chat_history_service.add_message(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Hi",
            status=MessageStatus.STREAMING,
        )


async def test_add_message_assistant_streaming_allowed(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="...",
        status=MessageStatus.STREAMING,
    )
    assert message.status == MessageStatus.STREAMING


async def test_add_message_invalid_parent_raises(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    first = await conversation_service.create_conversation(user_id=user.id)
    second = await conversation_service.create_conversation(user_id=user.id)
    parent = await chat_history_service.add_message(
        conversation_id=first.id, role=MessageRole.USER, content="Parent"
    )
    with pytest.raises(ValidationError):
        await chat_history_service.add_message(
            conversation_id=second.id,
            role=MessageRole.USER,
            content="Child",
            parent_message_id=parent.id,
        )


async def test_get_history_returns_chronological(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    first = await chat_history_service.add_message(
        conversation_id=conv.id, role=MessageRole.USER, content="One"
    )
    second = await chat_history_service.add_message(
        conversation_id=conv.id, role=MessageRole.ASSISTANT, content="Two"
    )
    history = await chat_history_service.get_history(conversation_id=conv.id)
    assert [message.id for message in history] == [first.id, second.id]


async def test_get_history_missing_conversation_raises(
    chat_history_service: ChatHistoryService,
) -> None:
    with pytest.raises(NotFoundError):
        await chat_history_service.get_history(conversation_id=uuid.uuid4())


async def test_update_message_status_completes_streaming(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="Answer",
        status=MessageStatus.QUEUED,
    )
    completed = await chat_history_service.update_message_status(
        message_id=message.id, status=MessageStatus.COMPLETED
    )
    assert completed.status == MessageStatus.COMPLETED


async def test_update_message_status_invalid_for_role_raises(
    conversation_service, chat_history_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    message = await chat_history_service.add_message(
        conversation_id=conv.id, role=MessageRole.USER, content="Hi"
    )
    with pytest.raises(ValidationError):
        await chat_history_service.update_message_status(
            message_id=message.id, status=MessageStatus.STREAMING
        )


async def test_update_message_status_missing_message_raises(
    chat_history_service: ChatHistoryService,
) -> None:
    with pytest.raises(NotFoundError):
        await chat_history_service.update_message_status(
            message_id=uuid.uuid4(), status=MessageStatus.COMPLETED
        )
