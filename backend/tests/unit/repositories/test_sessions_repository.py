"""``sessions`` repository helpers (DATABASE_DESIGN.md §25)."""

from __future__ import annotations

from datetime import timedelta

from app.repositories import SessionRepository
from app.utils.time import utc_now


async def test_get_by_refresh_hash_hit(db_session, session_factory) -> None:
    session = await session_factory()
    repo = SessionRepository(db_session)
    fetched = await repo.get_by_refresh_hash(session.refresh_token_hash)
    assert fetched is not None
    assert fetched.id == session.id


async def test_get_by_refresh_hash_miss(db_session, session_factory) -> None:
    await session_factory()
    repo = SessionRepository(db_session)
    assert await repo.get_by_refresh_hash("missing-hash") is None


async def test_revoke_session_sets_revoked_at(db_session, session_factory) -> None:
    session = await session_factory()
    repo = SessionRepository(db_session)
    revoked = await repo.revoke_session(session)
    assert revoked.revoked_at is not None


async def test_get_active_sessions_filters_and_orders(
    db_session, session_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    s1 = await session_factory(user_id=user.id, last_used_at=now)
    s2 = await session_factory(
        user_id=user.id, last_used_at=now - timedelta(minutes=1)
    )
    revoked = await session_factory(
        user_id=user.id, last_used_at=now - timedelta(minutes=2)
    )
    await session_factory(
        user_id=user.id,
        created_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
        last_used_at=now - timedelta(minutes=3),
    )
    other_user = await user_factory()
    await session_factory(user_id=other_user.id)
    repo = SessionRepository(db_session)
    await repo.revoke_session(revoked)
    rows = await repo.get_active_sessions(user.id)
    assert [row.id for row in rows] == [s1.id, s2.id]


async def test_delete_expired_purges_only_expired(
    db_session, session_factory, user_factory
) -> None:
    user = await user_factory()
    now = utc_now()
    expired = await session_factory(
        user_id=user.id,
        created_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
    )
    active = await session_factory(user_id=user.id)
    repo = SessionRepository(db_session)
    deleted = await repo.delete_expired()
    assert deleted == 1
    assert await repo.get_by_id(expired.id) is None
    assert await repo.get_by_id(active.id) is not None
