"""``requests`` and ``request_timeline`` repository helpers (DATABASE_DESIGN.md §17, §18)."""

from __future__ import annotations

from datetime import timedelta

from app.models import RequestStatus
from app.repositories import RequestRepository, RequestTimelineRepository
from app.utils.time import utc_now


async def test_get_by_request_no_hit(db_session, request_factory, user_factory) -> None:
    req = await request_factory(user_id=(await user_factory()).id, request_no="REQ-42")
    repo = RequestRepository(db_session)
    fetched = await repo.get_by_request_no("REQ-42")
    assert fetched is not None
    assert fetched.id == req.id


async def test_get_by_request_no_miss(db_session, request_factory, user_factory) -> None:
    await request_factory(user_id=(await user_factory()).id)
    repo = RequestRepository(db_session)
    assert await repo.get_by_request_no("REQ-NOPE") is None


async def test_get_pending_returns_active_statuses_oldest_first(
    db_session, request_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    old = await request_factory(
        user_id=user.id, status=RequestStatus.SUBMITTED, created_at=now - timedelta(minutes=10)
    )
    new = await request_factory(
        user_id=user.id, status=RequestStatus.PROCESSING, created_at=now - timedelta(minutes=1)
    )
    await request_factory(
        user_id=user.id, status=RequestStatus.DRAFT, created_at=now - timedelta(minutes=5)
    )
    await request_factory(
        user_id=user.id,
        status=RequestStatus.RESOLVED,
        resolved_at=now - timedelta(minutes=2),
    )
    await request_factory(
        user_id=user.id,
        status=RequestStatus.REJECTED,
        rejection_reason="nope",
    )
    repo = RequestRepository(db_session)
    rows = await repo.get_pending()
    assert [row.id for row in rows] == [old.id, new.id]


async def test_get_by_status_filters_and_orders_newest_first(
    db_session, request_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    r1 = await request_factory(
        user_id=user.id, status=RequestStatus.IN_REVIEW, created_at=now
    )
    r2 = await request_factory(
        user_id=user.id,
        status=RequestStatus.IN_REVIEW,
        created_at=now - timedelta(minutes=1),
    )
    await request_factory(
        user_id=user.id, status=RequestStatus.SUBMITTED, created_at=now - timedelta(minutes=2)
    )
    repo = RequestRepository(db_session)
    rows = await repo.get_by_status(RequestStatus.IN_REVIEW)
    assert [row.id for row in rows] == [r1.id, r2.id]


async def test_get_student_requests_paginates_newest_first(
    db_session, request_factory, user_factory
) -> None:
    user = await user_factory()
    other = await user_factory()
    now = utc_now()
    r1 = await request_factory(user_id=user.id, created_at=now)
    r2 = await request_factory(
        user_id=user.id, created_at=now - timedelta(minutes=1)
    )
    r3 = await request_factory(
        user_id=user.id, created_at=now - timedelta(minutes=2)
    )
    await request_factory(user_id=other.id, created_at=now - timedelta(minutes=3))
    repo = RequestRepository(db_session)
    page = await repo.get_student_requests(user.id, page=1, limit=2)
    assert [row.id for row in page.items] == [r1.id, r2.id]
    assert page.total == 3
    page2 = await repo.get_student_requests(user.id, page=2, limit=2)
    assert [row.id for row in page2.items] == [r3.id]


async def test_get_department_requests_paginates(
    db_session, request_factory, user_factory, department_factory
) -> None:
    user = await user_factory()
    dept = await department_factory()
    other_dept = await department_factory()
    now = utc_now()
    r1 = await request_factory(
        user_id=user.id, department_id=dept.id, created_at=now
    )
    r2 = await request_factory(
        user_id=user.id, department_id=dept.id, created_at=now - timedelta(minutes=1)
    )
    await request_factory(user_id=user.id, department_id=other_dept.id)
    repo = RequestRepository(db_session)
    page = await repo.get_department_requests(dept.id, limit=10)
    assert [row.id for row in page.items] == [r1.id, r2.id]
    assert page.total == 2


async def test_timeline_list_by_request_chronological(
    db_session, request_factory, request_timeline_factory, user_factory
) -> None:
    user = await user_factory()
    req = await request_factory(user_id=user.id)
    other_req = await request_factory(user_id=user.id)
    now = utc_now()
    t1 = await request_timeline_factory(
        request_id=req.id, action="first", created_at=now
    )
    t2 = await request_timeline_factory(
        request_id=req.id, action="second", created_at=now - timedelta(minutes=1)
    )
    await request_timeline_factory(request_id=other_req.id, action="other")
    repo = RequestTimelineRepository(db_session)
    rows = await repo.list_by_request(req.id)
    assert [row.id for row in rows] == [t2.id, t1.id]
