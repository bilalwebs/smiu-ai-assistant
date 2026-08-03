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
