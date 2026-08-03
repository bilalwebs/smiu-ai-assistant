"""``notifications`` repository helpers (DATABASE_DESIGN.md §19)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import NotificationRepository
from app.utils.time import utc_now


async def test_list_unread_newest_first(
    db_session, notification_factory, user_factory
) -> None:
    user = await user_factory()
    other = await user_factory()
    now = utc_now()
    n1 = await notification_factory(user_id=user.id, created_at=now)
    n2 = await notification_factory(
        user_id=user.id, created_at=now - timedelta(minutes=1)
    )
    read = await notification_factory(
        user_id=user.id, created_at=now - timedelta(minutes=2)
    )
    deleted = await notification_factory(
        user_id=user.id, created_at=now - timedelta(minutes=3)
    )
    await notification_factory(user_id=other.id)
    repo = NotificationRepository(db_session)
    await repo.mark_read(read)
    await repo.soft_delete(deleted)
    rows = await repo.list_unread(user.id)
    assert [row.id for row in rows] == [n1.id, n2.id]


async def test_count_unread(db_session, notification_factory, user_factory) -> None:
    user = await user_factory()
    await notification_factory(user_id=user.id)
    read = await notification_factory(user_id=user.id)
    deleted = await notification_factory(user_id=user.id)
    repo = NotificationRepository(db_session)
    await repo.mark_read(read)
    await repo.soft_delete(deleted)
    assert await repo.count_unread(user.id) == 1


async def test_mark_read_sets_read_at(db_session, notification_factory, user_factory) -> None:
    user = await user_factory()
    notification = await notification_factory(user_id=user.id)
    repo = NotificationRepository(db_session)
    marked = await repo.mark_read(notification)
    assert marked.read_at is not None
    assert await repo.count_unread(user.id) == 0
