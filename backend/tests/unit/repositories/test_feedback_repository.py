"""``feedback`` repository helpers (DATABASE_DESIGN.md §23)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import FeedbackRepository
from app.utils.time import utc_now


async def test_list_by_message_newest_first(
    db_session, feedback_factory, user_factory, conversation_factory, message_factory
) -> None:
    user = await user_factory()
    conv = await conversation_factory(user_id=user.id)
    msg = await message_factory(conversation_id=conv.id)
    other_msg = await message_factory(conversation_id=conv.id)
    now = utc_now()
    f1 = await feedback_factory(
        user_id=user.id, message_id=msg.id, comment="n1", created_at=now
    )
    f2 = await feedback_factory(
        user_id=user.id,
        message_id=msg.id,
        comment="n2",
        created_at=now - timedelta(minutes=1),
    )
    other = await user_factory()
    await feedback_factory(user_id=other.id, message_id=other_msg.id)
    repo = FeedbackRepository(db_session)
    rows = await repo.list_by_message(msg.id)
    assert [row.id for row in rows] == [f1.id, f2.id]


async def test_list_by_user_newest_first(
    db_session, feedback_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    f1 = await feedback_factory(user_id=user.id, comment="n1", created_at=now)
    f2 = await feedback_factory(
        user_id=user.id, comment="n2", created_at=now - timedelta(minutes=1)
    )
    repo = FeedbackRepository(db_session)
    rows = await repo.list_by_user(user.id)
    assert [row.id for row in rows] == [f1.id, f2.id]


async def test_list_by_user_excludes_soft_deleted(
    db_session, feedback_factory, user_factory
) -> None:
    user = await user_factory()
    live = await feedback_factory(user_id=user.id)
    gone = await feedback_factory(user_id=user.id)
    repo = FeedbackRepository(db_session)
    await repo.soft_delete(gone)
    rows = await repo.list_by_user(user.id)
    assert [row.id for row in rows] == [live.id]
