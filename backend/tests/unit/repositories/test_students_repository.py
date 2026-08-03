"""``students`` repository helpers (DATABASE_DESIGN.md §13)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import StudentRepository
from app.utils.time import utc_now


async def test_get_by_user_id_hit(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id)
    repo = StudentRepository(db_session)
    fetched = await repo.get_by_user_id(user.id)
    assert fetched is not None
    assert fetched.id == student.id


async def test_get_by_user_id_miss(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    await student_factory(user_id=user.id)
    other = await user_factory()
    repo = StudentRepository(db_session)
    assert await repo.get_by_user_id(other.id) is None


async def test_get_by_enrollment_no_hit(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id, enrollment_no="SMIU-ENROLL-1")
    repo = StudentRepository(db_session)
    fetched = await repo.get_by_enrollment_no("SMIU-ENROLL-1")
    assert fetched is not None
    assert fetched.id == student.id


async def test_get_by_enrollment_no_miss(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    await student_factory(user_id=user.id)
    repo = StudentRepository(db_session)
    assert await repo.get_by_enrollment_no("SMIU-NOPE") is None


async def test_get_by_user_id_excludes_soft_deleted(
    db_session, user_factory, student_factory
) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id)
    repo = StudentRepository(db_session)
    await repo.soft_delete(student)
    assert await repo.get_by_user_id(user.id) is None


async def test_list_by_department_filters_and_orders(
    db_session, user_factory, department_factory, student_factory
) -> None:
    dept = await department_factory()
    other_dept = await department_factory()
    now = utc_now()
    s1 = await student_factory(
        user_id=(await user_factory()).id,
        department_id=dept.id,
        created_at=now,
    )
    s2 = await student_factory(
        user_id=(await user_factory()).id,
        department_id=dept.id,
        created_at=now - timedelta(minutes=5),
    )
    await student_factory(user_id=(await user_factory()).id, department_id=other_dept.id)
    repo = StudentRepository(db_session)
    rows = await repo.list_by_department(dept.id)
    assert [row.id for row in rows] == [s1.id, s2.id]


async def test_list_by_department_excludes_soft_deleted(
    db_session, user_factory, department_factory, student_factory
) -> None:
    dept = await department_factory()
    live = await student_factory(
        user_id=(await user_factory()).id, department_id=dept.id
    )
    gone = await student_factory(
        user_id=(await user_factory()).id, department_id=dept.id
    )
    repo = StudentRepository(db_session)
    await repo.soft_delete(gone)
    rows = await repo.list_by_department(dept.id)
    assert [row.id for row in rows] == [live.id]
