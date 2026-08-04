"""``ai_conversations`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import ConversationStatus
from app.services import ConversationService
from app.services.exceptions import InvalidStateError, NotFoundError, ValidationError


async def test_create_conversation_happy_path(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(
        user_id=user.id, title="Admissions help"
    )
    assert conv.user_id == user.id
    assert conv.title == "Admissions help"
    assert conv.status == ConversationStatus.ACTIVE
    assert conv.message_count == 0


async def test_create_conversation_with_first_message(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(
        user_id=user.id, first_message="Hello"
    )
    assert conv.message_count == 1
    assert conv.last_message_at is not None


async def test_create_conversation_missing_user_raises(
    conversation_service: ConversationService,
) -> None:
    with pytest.raises(NotFoundError):
        await conversation_service.create_conversation(user_id=uuid.uuid4())


async def test_create_conversation_missing_department_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(NotFoundError):
        await conversation_service.create_conversation(
            user_id=user.id, department_id=uuid.uuid4()
        )


async def test_create_conversation_invalid_status_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await conversation_service.create_conversation(
            user_id=user.id, status=ConversationStatus.ARCHIVED
        )


async def test_create_conversation_blank_title_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await conversation_service.create_conversation(user_id=user.id, title="   ")


async def test_create_conversation_blank_first_message_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await conversation_service.create_conversation(
            user_id=user.id, first_message="  "
        )


async def test_update_conversation_title(conversation_service, user_factory) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id, title="Old")
    updated = await conversation_service.update_conversation(
        conversation_id=conv.id, title="New"
    )
    assert updated.title == "New"


async def test_update_conversation_blank_title_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    with pytest.raises(ValidationError):
        await conversation_service.update_conversation(
            conversation_id=conv.id, title=" "
        )


async def test_archive_and_restore_conversation(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    archived = await conversation_service.archive_conversation(conversation_id=conv.id)
    assert archived.status == ConversationStatus.ARCHIVED
    restored = await conversation_service.restore_conversation(conversation_id=conv.id)
    assert restored.status == ConversationStatus.ACTIVE


async def test_archive_non_active_conversation_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    await conversation_service.archive_conversation(conversation_id=conv.id)
    with pytest.raises(InvalidStateError):
        await conversation_service.archive_conversation(conversation_id=conv.id)


async def test_restore_active_conversation_raises(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    with pytest.raises(InvalidStateError):
        await conversation_service.restore_conversation(conversation_id=conv.id)


async def test_delete_conversation_soft_deletes(
    conversation_service, user_factory
) -> None:
    user = await user_factory()
    conv = await conversation_service.create_conversation(user_id=user.id)
    deleted = await conversation_service.delete_conversation(conversation_id=conv.id)
    assert deleted.is_deleted
    with pytest.raises(NotFoundError):
        await conversation_service.get_conversation(conversation_id=conv.id)


async def test_missing_conversation_raises(
    conversation_service: ConversationService,
) -> None:
    with pytest.raises(NotFoundError):
        await conversation_service.get_conversation(conversation_id=uuid.uuid4())


async def test_list_user_conversations_scoped_to_user(
    conversation_service, user_factory
) -> None:
    owner = await user_factory()
    other = await user_factory()
    await conversation_service.create_conversation(user_id=owner.id, title="Mine")
    await conversation_service.create_conversation(user_id=other.id, title="Theirs")
    page = await conversation_service.list_user_conversations(user_id=owner.id)
    assert page.total == 1
    assert page.items[0].title == "Mine"


async def test_list_user_conversations_missing_user_raises(
    conversation_service: ConversationService,
) -> None:
    with pytest.raises(NotFoundError):
        await conversation_service.list_user_conversations(user_id=uuid.uuid4())
