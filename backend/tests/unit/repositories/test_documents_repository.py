"""``documents`` repository helpers (DATABASE_DESIGN.md §20)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import DocumentRepository
from app.utils.time import utc_now


async def test_list_by_request_upload_order(
    db_session, document_factory, request_factory, user_factory
) -> None:
    user = await user_factory()
    req = await request_factory(user_id=user.id)
    other_req = await request_factory(user_id=user.id)
    now = utc_now()
    d1 = await document_factory(
        request_id=req.id, original_filename="a.pdf", created_at=now
    )
    d2 = await document_factory(
        request_id=req.id, original_filename="b.pdf", created_at=now - timedelta(minutes=1)
    )
    await document_factory(request_id=other_req.id)
    repo = DocumentRepository(db_session)
    rows = await repo.list_by_request(req.id)
    assert [row.id for row in rows] == [d2.id, d1.id]


async def test_list_by_user_newest_first(
    db_session, document_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    d1 = await document_factory(
        user_id=user.id, original_filename="n1.pdf", created_at=now
    )
    d2 = await document_factory(
        user_id=user.id, original_filename="n2.pdf", created_at=now - timedelta(minutes=1)
    )
    repo = DocumentRepository(db_session)
    rows = await repo.list_by_user(user.id)
    assert [row.id for row in rows] == [d1.id, d2.id]


async def test_lists_exclude_soft_deleted(
    db_session, document_factory, request_factory, user_factory
) -> None:
    user = await user_factory()
    req = await request_factory(user_id=user.id)
    live = await document_factory(request_id=req.id)
    gone = await document_factory(request_id=req.id)
    repo = DocumentRepository(db_session)
    await repo.soft_delete(gone)
    rows = await repo.list_by_request(req.id)
    assert [row.id for row in rows] == [live.id]


async def test_list_by_conversation_returns_linked_docs(
    db_session, document_factory, user_factory, conversation_factory, message_factory
) -> None:
    user = await user_factory()
    conv = await conversation_factory(user_id=user.id)
    msg = await message_factory(conversation_id=conv.id)
    d1 = await document_factory(user_id=user.id, message_id=msg.id)
    d2 = await document_factory(user_id=user.id, message_id=msg.id)
    # Unlinked doc should not appear
    await document_factory(user_id=user.id)
    repo = DocumentRepository(db_session)
    rows = await repo.list_by_conversation(conv.id)
    assert {row.id for row in rows} == {d1.id, d2.id}


async def test_list_by_conversation_excludes_other_conversations(
    db_session, document_factory, user_factory, conversation_factory, message_factory
) -> None:
    user = await user_factory()
    conv_a = await conversation_factory(user_id=user.id)
    conv_b = await conversation_factory(user_id=user.id)
    msg_a = await message_factory(conversation_id=conv_a.id)
    msg_b = await message_factory(conversation_id=conv_b.id)
    d_a = await document_factory(user_id=user.id, message_id=msg_a.id)
    await document_factory(user_id=user.id, message_id=msg_b.id)
    repo = DocumentRepository(db_session)
    rows = await repo.list_by_conversation(conv_a.id)
    assert [row.id for row in rows] == [d_a.id]


async def test_list_by_conversation_excludes_soft_deleted(
    db_session, document_factory, user_factory, conversation_factory, message_factory
) -> None:
    user = await user_factory()
    conv = await conversation_factory(user_id=user.id)
    msg = await message_factory(conversation_id=conv.id)
    live = await document_factory(user_id=user.id, message_id=msg.id)
    gone = await document_factory(user_id=user.id, message_id=msg.id)
    repo = DocumentRepository(db_session)
    await repo.soft_delete(gone)
    rows = await repo.list_by_conversation(conv.id)
    assert [row.id for row in rows] == [live.id]
