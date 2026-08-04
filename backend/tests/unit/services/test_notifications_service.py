"""``notifications`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid

import pytest

from app.models import NotificationPriority, NotificationType
from app.services import NotificationService
from app.services.exceptions import InvalidStateError, NotFoundError, ValidationError


async def test_create_notification_happy_path(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    notif = await notification_service.create_notification(
        user_id=user.id, type=NotificationType.REQUEST, title="Status update"
    )
    assert notif.user_id == user.id
    assert notif.type == NotificationType.REQUEST
    assert notif.priority == NotificationPriority.MEDIUM
    assert notif.read_at is None


async def test_create_notification_explicit_priority(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    notif = await notification_service.create_notification(
        user_id=user.id,
        type=NotificationType.AI,
        title="New answer",
        priority=NotificationPriority.HIGH,
    )
    assert notif.priority == NotificationPriority.HIGH


async def test_create_notification_missing_user_raises(
    notification_service: NotificationService,
) -> None:
    with pytest.raises(NotFoundError):
        await notification_service.create_notification(
            user_id=uuid.uuid4(), type=NotificationType.SYSTEM, title="Hello"
        )


async def test_create_notification_missing_request_raises(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(NotFoundError):
        await notification_service.create_notification(
            user_id=user.id,
            type=NotificationType.REQUEST,
            title="Hello",
            request_id=uuid.uuid4(),
        )


async def test_create_notification_blank_title_raises(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await notification_service.create_notification(
            user_id=user.id, type=NotificationType.SYSTEM, title="  "
        )


async def test_create_notification_invalid_type_raises(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await notification_service.create_notification(
            user_id=user.id, type="bogus", title="Hello"
        )


async def test_mark_read(notification_service, user_factory) -> None:
    user = await user_factory()
    notif = await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="Hello"
    )
    marked = await notification_service.mark_read(notification_id=notif.id)
    assert marked.read_at is not None


async def test_mark_read_twice_raises(notification_service, user_factory) -> None:
    user = await user_factory()
    notif = await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="Hello"
    )
    await notification_service.mark_read(notification_id=notif.id)
    with pytest.raises(InvalidStateError):
        await notification_service.mark_read(notification_id=notif.id)


async def test_mark_read_missing_raises(
    notification_service: NotificationService,
) -> None:
    with pytest.raises(NotFoundError):
        await notification_service.mark_read(notification_id=uuid.uuid4())


async def test_mark_all_read_returns_count(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="A"
    )
    await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="B"
    )
    count = await notification_service.mark_all_read(user_id=user.id)
    assert count == 2
    assert await notification_service.count_unread(user_id=user.id) == 0


async def test_mark_all_read_missing_user_raises(
    notification_service: NotificationService,
) -> None:
    with pytest.raises(NotFoundError):
        await notification_service.mark_all_read(user_id=uuid.uuid4())


async def test_list_user_notifications_filtered_by_read(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    read_one = await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="A"
    )
    await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="B"
    )
    await notification_service.mark_read(notification_id=read_one.id)
    unread_page = await notification_service.list_user_notifications(
        user_id=user.id, read=False
    )
    assert len(unread_page.items) == 1
    assert unread_page.items[0].title == "B"
    read_page = await notification_service.list_user_notifications(
        user_id=user.id, read=True
    )
    assert len(read_page.items) == 1
    assert read_page.items[0].title == "A"


async def test_count_unread(notification_service, user_factory) -> None:
    user = await user_factory()
    assert await notification_service.count_unread(user_id=user.id) == 0
    await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="A"
    )
    assert await notification_service.count_unread(user_id=user.id) == 1


async def test_delete_notification_soft_deletes(
    notification_service, user_factory
) -> None:
    user = await user_factory()
    notif = await notification_service.create_notification(
        user_id=user.id, type=NotificationType.SYSTEM, title="Hello"
    )
    deleted = await notification_service.delete_notification(notification_id=notif.id)
    assert deleted.is_deleted
