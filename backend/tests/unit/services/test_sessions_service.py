"""``sessions`` service tests (TESTING_STRATEGY.md §26)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import UserSession
from app.services import SessionService
from app.services.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)


def _future(seconds: int = 3600) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


async def test_create_session_happy_path(session_service, user_factory) -> None:
    user = await user_factory()
    session = await session_service.create_session(
        user_id=user.id,
        refresh_token_hash="a" * 64,
        expires_at=_future(),
        device_name="Chrome on Windows",
        ip_address="192.168.1.1",
        user_agent="pytest",
        access_jti="jti-123",
    )
    assert isinstance(session, UserSession)
    assert session.user_id == user.id
    assert session.refresh_token_hash == "a" * 64
    assert session.revoked_at is None


async def test_create_session_missing_user_raises(
    session_service: SessionService,
) -> None:
    with pytest.raises(NotFoundError):
        await session_service.create_session(
            user_id=uuid.uuid4(), refresh_token_hash="a" * 64, expires_at=_future()
        )


async def test_create_session_past_expiry_raises(session_service, user_factory) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await session_service.create_session(
            user_id=user.id,
            refresh_token_hash="a" * 64,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )


async def test_create_session_duplicate_hash_raises(
    session_service, user_factory
) -> None:
    user = await user_factory()
    await session_service.create_session(
        user_id=user.id, refresh_token_hash="b" * 64, expires_at=_future()
    )
    with pytest.raises(ConflictError):
        await session_service.create_session(
            user_id=user.id, refresh_token_hash="b" * 64, expires_at=_future()
        )


async def test_create_session_blank_or_too_long_hash_raises(
    session_service, user_factory
) -> None:
    user = await user_factory()
    with pytest.raises(ValidationError):
        await session_service.create_session(
            user_id=user.id, refresh_token_hash="   ", expires_at=_future()
        )
    with pytest.raises(ValidationError):
        await session_service.create_session(
            user_id=user.id, refresh_token_hash="c" * 65, expires_at=_future()
        )


async def test_revoke_session_happy_path(session_service, user_factory) -> None:
    user = await user_factory()
    session = await session_service.create_session(
        user_id=user.id, refresh_token_hash="d" * 64, expires_at=_future()
    )
    revoked = await session_service.revoke_session(session_id=session.id)
    assert revoked.revoked_at is not None


async def test_revoke_session_already_revoked_raises(
    session_service, user_factory
) -> None:
    user = await user_factory()
    session = await session_service.create_session(
        user_id=user.id, refresh_token_hash="e" * 64, expires_at=_future()
    )
    await session_service.revoke_session(session_id=session.id)
    with pytest.raises(InvalidStateError):
        await session_service.revoke_session(session_id=session.id)


async def test_revoke_session_missing_raises(session_service: SessionService) -> None:
    with pytest.raises(NotFoundError):
        await session_service.revoke_session(session_id=uuid.uuid4())


async def test_revoke_all_sessions_revokes_and_counts(
    session_service, user_factory
) -> None:
    user = await user_factory()
    for i in range(3):
        await session_service.create_session(
            user_id=user.id,
            refresh_token_hash=f"{i}" * 64,
            expires_at=_future(),
        )
    count = await session_service.revoke_all_sessions(user_id=user.id)
    assert count == 3


async def test_revoke_all_sessions_no_active_returns_zero(
    session_service, user_factory
) -> None:
    user = await user_factory()
    count = await session_service.revoke_all_sessions(user_id=user.id)
    assert count == 0


async def test_revoke_all_sessions_missing_user_raises(
    session_service: SessionService,
) -> None:
    with pytest.raises(NotFoundError):
        await session_service.revoke_all_sessions(user_id=uuid.uuid4())


async def test_list_active_sessions_paginates_active_only(
    session_service, user_factory
) -> None:
    user = await user_factory()
    for i in range(3):
        await session_service.create_session(
            user_id=user.id,
            refresh_token_hash=f"f{i}" * 32,
            expires_at=_future(),
        )
    page = await session_service.list_active_sessions(user_id=user.id)
    assert page.total == 3
    assert len(page.items) == 3

    await session_service.revoke_session(session_id=page.items[0].id)
    page_after = await session_service.list_active_sessions(user_id=user.id)
    assert page_after.total == 2


async def test_list_active_sessions_missing_user_raises(
    session_service: SessionService,
) -> None:
    with pytest.raises(NotFoundError):
        await session_service.list_active_sessions(user_id=uuid.uuid4())
