"""Generic ``BaseRepository`` behavior (BACKEND_ARCHITECTURE §12; DATABASE_DESIGN §26/§31/§34).

Covers CRUD, the default soft-delete scope, filtering/ordering, offset and
keyset pagination, optimistic-version bumps, and the never-commit rule.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserStatus
from app.repositories import UserRepository


async def test_create_refreshes_server_defaults(
    db_session: AsyncSession, user_factory: Callable[..., Awaitable[User]]
) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(
        email="alice@example.com",
        password_hash="hashed",
        full_name="Alice",
    )
    assert user.id is not None
    assert user.role == "student"
    assert user.status == "pending"
    assert user.version == 1


async def test_get_by_id_round_trip(db_session, user_factory) -> None:
    created = await user_factory()
    repo = UserRepository(db_session)
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == created.email


async def test_get_by_id_missing_returns_none(db_session) -> None:
    repo = UserRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_single_match(db_session, user_factory) -> None:
    user = await user_factory(email="only@example.com")
    repo = UserRepository(db_session)
    assert (await repo.get(User.email == "only@example.com")).id == user.id


async def test_get_one_no_match_raises(db_session) -> None:
    repo = UserRepository(db_session)
    with pytest.raises(NoResultFound):
        await repo.get_one(User.email == "missing@example.com")


async def test_get_one_multiple_matches_raises(db_session, user_factory) -> None:
    await user_factory()
    await user_factory()
    repo = UserRepository(db_session)
    with pytest.raises(MultipleResultsFound):
        await repo.get_one(User.full_name == "Test User")


async def test_update_applies_values_and_bumps_version(db_session, user_factory) -> None:
    user = await user_factory(full_name="Old Name")
    repo = UserRepository(db_session)
    updated = await repo.update(user, full_name="New Name")
    assert updated.full_name == "New Name"
    assert updated.version == 2


async def test_update_unknown_attribute_raises(db_session, user_factory) -> None:
    user = await user_factory()
    repo = UserRepository(db_session)
    with pytest.raises(ValueError):
        await repo.update(user, nonexistent="x")


async def test_soft_delete_scopes_live_rows(db_session, user_factory) -> None:
    user = await user_factory()
    repo = UserRepository(db_session)
    await repo.soft_delete(user)
    assert user.is_deleted is True
    assert await repo.get_by_id(user.id) is None
    assert await repo.count() == 0
    assert await repo.exists() is False


async def test_restore_brings_row_back(db_session, user_factory) -> None:
    user = await user_factory()
    repo = UserRepository(db_session)
    await repo.soft_delete(user)
    await repo.restore(user)
    assert user.is_deleted is False
    assert await repo.get_by_id(user.id) is not None


async def test_hard_delete_removes_row(db_session, user_factory) -> None:
    user = await user_factory()
    repo = UserRepository(db_session)
    await repo.delete(user)
    assert await repo.count() == 0
    assert await repo.get_by_id(user.id) is None


async def test_list_filters_and_orders(db_session, user_factory) -> None:
    await user_factory(full_name="Zed")
    await user_factory(full_name="Amy")
    repo = UserRepository(db_session)
    rows = await repo.list(order_by=[User.full_name.asc()])
    assert [row.full_name for row in rows] == ["Amy", "Zed"]

    rows = await repo.list(User.full_name == "Zed")
    assert [row.full_name for row in rows] == ["Zed"]

    rows = await repo.list(order_by=[User.full_name.asc()], limit=1, offset=1)
    assert [row.full_name for row in rows] == ["Zed"]


async def test_count_and_exists_with_filters(db_session, user_factory) -> None:
    await user_factory()
    await user_factory(status=UserStatus.ACTIVE)
    repo = UserRepository(db_session)
    assert await repo.count() == 2
    assert await repo.count(User.status == UserStatus.ACTIVE) == 1
    assert await repo.exists(User.status == UserStatus.ACTIVE) is True
    assert await repo.exists(User.status == UserStatus.SUSPENDED) is False


async def test_paginate_contract(db_session, user_factory) -> None:
    for _ in range(5):
        await user_factory()
    repo = UserRepository(db_session)

    first = await repo.paginate(page=1, limit=2)
    assert len(first.items) == 2
    assert first.page == 1
    assert first.limit == 2
    assert first.offset == 0
    assert first.total == 5
    assert first.total_pages == 3
    assert first.next_page == 2
    assert first.prev_page is None

    middle = await repo.paginate(page=2, limit=2)
    assert len(middle.items) == 2
    assert middle.offset == 2
    assert middle.next_page == 3
    assert middle.prev_page == 1

    last = await repo.paginate(page=3, limit=2)
    assert len(last.items) == 1
    assert last.next_page is None
    assert last.prev_page == 2

    beyond = await repo.paginate(page=9, limit=2)
    assert beyond.items == []
    assert beyond.next_page is None


async def test_paginate_empty_collection(db_session) -> None:
    repo = UserRepository(db_session)
    page = await repo.paginate()
    assert page.items == []
    assert page.total == 0
    assert page.total_pages == 0
    assert page.next_page is None
    assert page.prev_page is None


async def test_paginate_clamps_invalid_inputs(db_session, user_factory) -> None:
    await user_factory()
    repo = UserRepository(db_session)
    page = await repo.paginate(page=0, limit=0)
    assert page.page == 1
    assert page.limit == 1
    assert page.total == 1


async def test_paginate_keyset_desc(db_session, user_factory) -> None:
    for _ in range(7):
        await user_factory()
    repo = UserRepository(db_session)

    first = await repo.paginate_keyset(limit=3)
    assert len(first.items) == 3
    assert first.has_more is True
    assert first.next_cursor is not None

    second = await repo.paginate_keyset(limit=3, cursor=first.next_cursor)
    assert len(second.items) == 3
    assert second.has_more is True

    third = await repo.paginate_keyset(limit=3, cursor=second.next_cursor)
    assert len(third.items) == 1
    assert third.has_more is False
    assert third.next_cursor is None

    all_ids = {user.id for user in first.items + second.items + third.items}
    assert len(all_ids) == 7


async def test_paginate_keyset_asc_no_overlap(db_session, user_factory) -> None:
    for _ in range(4):
        await user_factory()
    repo = UserRepository(db_session)

    first = await repo.paginate_keyset(limit=2, descending=False)
    assert first.has_more is True
    second = await repo.paginate_keyset(
        limit=2, cursor=first.next_cursor, descending=False
    )
    assert second.has_more is False
    assert second.next_cursor is None
    all_ids = {user.id for user in first.items + second.items}
    assert len(all_ids) == 4


async def test_repository_never_commits(db_session) -> None:
    repo = UserRepository(db_session)
    await repo.create(email="tmp@example.com", password_hash="x", full_name="Tmp")
    await db_session.rollback()
    assert await repo.count() == 0


async def test_duplicate_unique_field_raises_integrity(db_session, user_factory) -> None:
    await user_factory(email="dup@example.com")
    repo = UserRepository(db_session)
    with pytest.raises(IntegrityError):
        await repo.create(
            email="dup@example.com", password_hash="x", full_name="Dup"
        )


async def test_eager_loading_options(db_session, user_factory, session_factory) -> None:
    user = await user_factory()
    await session_factory(user_id=user.id)
    db_session.expunge(user)
    repo = UserRepository(db_session)
    fetched = await repo.get_by_id(user.id, options=[selectinload(User.sessions)])
    assert fetched is not None
    assert [session.user_id for session in fetched.sessions] == [user.id]
