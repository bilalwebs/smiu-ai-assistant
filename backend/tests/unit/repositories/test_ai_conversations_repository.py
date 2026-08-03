"""``ai_conversations`` repository helpers (DATABASE_DESIGN.md §15, §16)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import ChatMessageRepository, ConversationRepository
from app.utils.time import utc_now


async def test_get_history_paginates_and_orders(
    db_session, user_factory, conversation_factory
) -> None:
    user = await user_factory()
    other = await user_factory()
    now = utc_now()
    c1 = await conversation_factory(user_id=user.id, last_message_at=now)
    c2 = await conversation_factory(
        user_id=user.id, last_message_at=now - timedelta(minutes=1)
    )
    c3 = await conversation_factory(user_id=user.id)
    await conversation_factory(user_id=other.id, last_message_at=now - timedelta(minutes=2))
    repo = ConversationRepository(db_session)
    page = await repo.get_history(user.id, page=1, limit=2)
    assert [row.id for row in page.items] == [c1.id, c2.id]
    assert page.total == 3
    page2 = await repo.get_history(user.id, page=2, limit=2)
    assert [row.id for row in page2.items] == [c3.id]
    assert page2.next_page is None


async def test_get_recent_messages_newest_window_oldest_first(
    db_session, user_factory, conversation_factory, message_factory
) -> None:
    conv = await conversation_factory(user_id=(await user_factory()).id)
    now = utc_now()
    await message_factory(conversation_id=conv.id, content="n1", created_at=now)
    await message_factory(
        conversation_id=conv.id, content="n2", created_at=now - timedelta(minutes=1)
    )
    await message_factory(
        conversation_id=conv.id, content="n3", created_at=now - timedelta(minutes=2)
    )
    await message_factory(
        conversation_id=conv.id, content="n4", created_at=now - timedelta(minutes=3)
    )
    repo = ConversationRepository(db_session)
    rows = await repo.get_recent_messages(conv.id, limit=3)
    assert [row.content for row in rows] == ["n3", "n2", "n1"]


async def test_get_recent_messages_excludes_soft_deleted(
    db_session, user_factory, conversation_factory, message_factory
) -> None:
    conv = await conversation_factory(user_id=(await user_factory()).id)
    now = utc_now()
    await message_factory(conversation_id=conv.id, content="n1", created_at=now)
    await message_factory(
        conversation_id=conv.id, content="n2", created_at=now - timedelta(minutes=1)
    )
    await message_factory(
        conversation_id=conv.id, content="n3", created_at=now - timedelta(minutes=2)
    )
    repo = ConversationRepository(db_session)
    chat_repo = ChatMessageRepository(db_session)
    window = await repo.get_recent_messages(conv.id)
    await chat_repo.soft_delete(window[-1])
    rows = await repo.get_recent_messages(conv.id)
    assert [row.content for row in rows] == ["n3", "n2"]


async def test_get_recent_messages_scopes_to_conversation(
    db_session, user_factory, conversation_factory, message_factory
) -> None:
    conv = await conversation_factory(user_id=(await user_factory()).id)
    other_conv = await conversation_factory(user_id=(await user_factory()).id)
    await message_factory(conversation_id=conv.id, content="mine")
    await message_factory(conversation_id=other_conv.id, content="theirs")
    repo = ConversationRepository(db_session)
    rows = await repo.get_recent_messages(conv.id)
    assert [row.content for row in rows] == ["mine"]
