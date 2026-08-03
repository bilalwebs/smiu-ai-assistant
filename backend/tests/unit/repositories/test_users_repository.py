"""``users`` repository helpers (DATABASE_DESIGN.md §12)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from app.models import UserStatus
from app.repositories import StudentRepository, UserRepository
from app.utils.time import utc_now


async def test_get_by_email_hit(db_session, user_factory) -> None:
    user = await user_factory(email="lookup@example.com")
    repo = UserRepository(db_session)
    fetched = await repo.get_by_email("lookup@example.com")
    assert fetched is not None
    assert fetched.id == user.id


async def test_get_by_email_miss(db_session, user_factory) -> None:
    await user_factory()
    repo = UserRepository(db_session)
    assert await repo.get_by_email("nope@example.com") is None


async def test_get_by_email_excludes_soft_deleted(db_session, user_factory) -> None:
    user = await user_factory(email="gone@example.com")
    repo = UserRepository(db_session)
    await repo.soft_delete(user)
    assert await repo.get_by_email("gone@example.com") is None


async def test_get_by_student_id_hit(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id)
    repo = UserRepository(db_session)
    fetched = await repo.get_by_student_id(student.id)
    assert fetched is not None
    assert fetched.id == user.id


async def test_get_by_student_id_missing(db_session, user_factory, student_factory) -> None:
    user = await user_factory()
    await student_factory(user_id=user.id)
    repo = UserRepository(db_session)
    assert await repo.get_by_student_id(uuid.uuid4()) is None


async def test_get_by_student_id_excludes_soft_deleted_student(
    db_session, user_factory, student_factory
) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id)
    repo = UserRepository(db_session)
    await StudentRepository(db_session).soft_delete(student)
    assert await repo.get_by_student_id(student.id) is None


async def test_get_by_student_id_excludes_soft_deleted_user(
    db_session, user_factory, student_factory
) -> None:
    user = await user_factory()
    student = await student_factory(user_id=user.id)
    repo = UserRepository(db_session)
    await repo.soft_delete(user)
    assert await repo.get_by_student_id(student.id) is None


async def test_get_active_users_filters_and_orders(db_session, user_factory) -> None:
    now = utc_now()
    active_new = await user_factory(
        status=UserStatus.ACTIVE, created_at=now
    )
    await user_factory(status=UserStatus.PENDING, created_at=now - timedelta(minutes=1))
    active_old = await user_factory(
        status=UserStatus.ACTIVE, created_at=now - timedelta(minutes=3)
    )
    await user_factory(status=UserStatus.SUSPENDED, created_at=now - timedelta(minutes=2))
    repo = UserRepository(db_session)
    rows = await repo.get_active_users()
    assert [row.id for row in rows] == [active_new.id, active_old.id]
