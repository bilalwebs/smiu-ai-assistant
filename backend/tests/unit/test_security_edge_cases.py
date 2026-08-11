"""Security edge-case tests (Milestone 4; Phase 6).

Complements ``tests/unit/test_security_hardening.py`` with negative-path
coverage: JWT algorithm confusion and claim tampering, bearer parsing edge
cases, fail-closed RBAC guards, refresh-token digest storage, full-chain
replay revocation, concurrent-session limiting, and user-enumeration
resistance.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.security.jwt import (
    CLAIM_TYPE,
    TOKEN_TYPE_ACCESS,
    create_access_token,
    decode_token,
    hash_refresh_token,
)
from app.core.security.password import hash_password_async
from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.rbac import require_permission, require_roles
from app.exceptions.app_error import ForbiddenError, UnauthorizedError
from app.models import User, UserRole, UserStatus
from app.repositories import SessionRepository, UserRepository
from app.services import AuthService, SessionService
from app.utils.time import utc_now

PASSWORD = "Sup3r!secure"


@pytest.fixture()
def user_factory(db_session: AsyncSession) -> Any:
    """Create a user row directly through the repository (no service calls)."""

    async def _make(**overrides: Any) -> User:
        values: dict[str, Any] = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password_hash": "hashed-password",
            "full_name": "Test User",
        }
        values.update(overrides)
        return await UserRepository(db_session).create(**values)

    return _make


async def _verified_user(user_factory, *, status: UserStatus = UserStatus.ACTIVE) -> User:
    password_hash = await hash_password_async(PASSWORD)
    return await user_factory(
        password_hash=password_hash,
        status=status,
        email_verified_at=utc_now(),
    )


# ---------------------------------------------------------------------------
# JWT algorithm validation & invalid tokens
# ---------------------------------------------------------------------------


def _base_payload(settings: Settings) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "sub": "user-1",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        CLAIM_TYPE: TOKEN_TYPE_ACCESS,
        "role": "student",
    }


class TestJWTSecurity:
    def test_hs384_token_rejected_when_hs256_configured(self) -> None:
        """A token signed with a non-configured HS algorithm is rejected."""
        settings = get_settings()
        token = pyjwt.encode(
            _base_payload(settings), settings.jwt_secret, algorithm="HS384"
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)

    def test_tampered_role_claim_rejected(self) -> None:
        """Escalating the role claim invalidates the signature."""
        settings = get_settings()
        token = create_access_token(subject="user-1", role="student", settings=settings)
        header, payload, _ = token.split(".")
        padded = payload + "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        claims["role"] = "admin"
        forged_payload = base64.urlsafe_b64encode(
            json.dumps(claims).encode()
        ).decode().rstrip("=")
        forged = f"{header}.{forged_payload}.AAA"
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=forged, expected_type=TOKEN_TYPE_ACCESS, settings=settings)

    def test_wrong_issuer_rejected(self) -> None:
        settings = get_settings()
        token = pyjwt.encode(
            {**_base_payload(settings), "iss": "evil-issuer"},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)

    def test_wrong_audience_rejected(self) -> None:
        settings = get_settings()
        token = pyjwt.encode(
            {**_base_payload(settings), "aud": "evil-audience"},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)

    def test_missing_required_claim_rejected(self) -> None:
        settings = get_settings()
        payload = _base_payload(settings)
        del payload["jti"]
        token = pyjwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)


# ---------------------------------------------------------------------------
# Bearer parsing edge cases (get_current_user)
# ---------------------------------------------------------------------------


def _make_request(headers: dict[str, str] | None = None) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/users/me",
        "headers": [
            (key.lower().encode("ascii"), value.encode("ascii"))
            for key, value in (headers or {}).items()
        ],
    }
    return Request(scope)


class TestBearerParsing:
    def test_missing_authorization_raises_401(self) -> None:
        with pytest.raises(UnauthorizedError):
            get_current_user(_make_request())

    def test_empty_authorization_raises_401(self) -> None:
        with pytest.raises(UnauthorizedError):
            get_current_user(_make_request(headers={"Authorization": ""}))

    def test_header_without_scheme_raises_401(self) -> None:
        with pytest.raises(UnauthorizedError):
            get_current_user(_make_request(headers={"Authorization": "plain-token"}))

    def test_wrong_scheme_raises_401(self) -> None:
        with pytest.raises(UnauthorizedError):
            get_current_user(
                _make_request(headers={"Authorization": "Basic dXNlcjpwYXNz"})
            )

    def test_empty_bearer_token_raises_401(self) -> None:
        with pytest.raises(UnauthorizedError):
            get_current_user(_make_request(headers={"Authorization": "Bearer "}))

    def test_case_insensitive_scheme_accepted(self) -> None:
        settings = get_settings()
        token = create_access_token(
            subject=str(uuid.uuid4()), role="student", settings=settings
        )
        current = get_current_user(
            _make_request(headers={"Authorization": f"bearer {token}"})
        )
        assert current.user_id is not None

    def test_valid_token_resolves_identity_and_role(self) -> None:
        settings = get_settings()
        user_id = uuid.uuid4()
        token = create_access_token(
            subject=str(user_id),
            role="admin",
            settings=settings,
            jti="session-jti",
        )
        current = get_current_user(
            _make_request(headers={"Authorization": f"Bearer {token}"})
        )
        assert current.user_id == user_id
        assert current.role == "admin"
        assert current.session_jti == "session-jti"

    def test_token_without_role_claim_raises_401(self) -> None:
        settings = get_settings()
        payload = _base_payload(settings)
        del payload["role"]
        token = pyjwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(UnauthorizedError):
            get_current_user(
                _make_request(headers={"Authorization": f"Bearer {token}"})
            )

    def test_expired_access_token_raises_401(self) -> None:
        settings = get_settings()
        now = datetime.now(UTC)
        payload = {
            **_base_payload(settings),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        }
        token = pyjwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(UnauthorizedError):
            get_current_user(
                _make_request(headers={"Authorization": f"Bearer {token}"})
            )


# ---------------------------------------------------------------------------
# Authorization edge cases (RBAC guards)
# ---------------------------------------------------------------------------


class TestRBACGuards:
    def _current(self, role: str) -> CurrentUser:
        return CurrentUser(user_id=uuid.uuid4(), role=role)

    def test_require_roles_grants_matching_role(self) -> None:
        guard = require_roles(UserRole.ADMIN)
        assert guard(self._current("admin")).role == "admin"

    def test_require_roles_denies_non_matching_role(self) -> None:
        guard = require_roles(UserRole.ADMIN)
        with pytest.raises(ForbiddenError):
            guard(self._current("student"))

    def test_require_roles_with_no_roles_denies_everyone(self) -> None:
        guard = require_roles()
        with pytest.raises(ForbiddenError):
            guard(self._current("admin"))

    def test_require_permission_allows_admin(self) -> None:
        guard = require_permission("users:list")
        assert guard(self._current("admin")).role == "admin"

    def test_require_permission_denies_student(self) -> None:
        guard = require_permission("users:list")
        with pytest.raises(ForbiddenError):
            guard(self._current("student"))

    def test_require_permission_unknown_permission_fails_closed(self) -> None:
        guard = require_permission("users:delete")
        with pytest.raises(ForbiddenError):
            guard(self._current("admin"))

    def test_unknown_role_value_fails_closed(self) -> None:
        guard = require_roles(UserRole.ADMIN)
        with pytest.raises(ForbiddenError):
            guard(self._current("superuser"))


# ---------------------------------------------------------------------------
# Refresh-token storage & replay
# ---------------------------------------------------------------------------


async def test_refresh_token_stored_as_sha256_digest(
    user_factory, db_session
) -> None:
    service = AuthService(db_session)
    user = await _verified_user(user_factory)
    login = await service.login(email=user.email, password=PASSWORD)
    session = await SessionRepository(db_session).get_by_refresh_hash(
        hash_refresh_token(login.refresh_token)
    )
    assert session is not None
    assert session.refresh_token_hash != login.refresh_token
    assert session.refresh_token_hash == hash_refresh_token(login.refresh_token)
    assert len(session.refresh_token_hash) == 64


async def test_replay_revokes_entire_rotation_chain(
    user_factory, db_session
) -> None:
    """Reusing an old refresh token revokes the newest chain link too."""
    service = AuthService(db_session)
    user = await _verified_user(user_factory)
    login = await service.login(email=user.email, password=PASSWORD)
    rotated = await service.rotate_refresh(refresh_token=login.refresh_token)

    with pytest.raises(UnauthorizedError):
        await service.rotate_refresh(refresh_token=login.refresh_token)
    with pytest.raises(UnauthorizedError):
        await service.rotate_refresh(refresh_token=rotated.refresh_token)


async def test_logout_revokes_all_other_sessions_after_replay(
    user_factory, db_session
) -> None:
    """Replay detection revokes every session sharing the rotation chain."""
    service = AuthService(db_session)
    user = await _verified_user(user_factory)
    login = await service.login(email=user.email, password=PASSWORD)
    rotated = await service.rotate_refresh(refresh_token=login.refresh_token)
    sessions = SessionRepository(db_session)

    with pytest.raises(UnauthorizedError):
        await service.rotate_refresh(refresh_token=login.refresh_token)

    first = await sessions.get_by_refresh_hash(hash_refresh_token(login.refresh_token))
    second = await sessions.get_by_refresh_hash(
        hash_refresh_token(rotated.refresh_token)
    )
    assert first is not None and first.revoked_at is not None
    assert second is not None and second.revoked_at is not None


# ---------------------------------------------------------------------------
# Concurrent session limiting
# ---------------------------------------------------------------------------


async def test_max_active_sessions_revokes_oldest(
    user_factory, db_session
) -> None:
    settings = get_settings().model_copy(update={"max_active_sessions": 2})
    service = AuthService(db_session, settings=settings)
    user = await _verified_user(user_factory)

    now = utc_now()
    session_service = SessionService(db_session)
    older = await session_service.create_session(
        user_id=user.id,
        refresh_token_hash="1" * 64,
        expires_at=now + timedelta(days=7),
    )
    older.created_at = now - timedelta(minutes=10)
    newer = await session_service.create_session(
        user_id=user.id,
        refresh_token_hash="2" * 64,
        expires_at=now + timedelta(days=7),
    )
    newer.created_at = now - timedelta(minutes=5)
    await db_session.flush()

    await service.login(email=user.email, password=PASSWORD)

    sessions = SessionRepository(db_session)
    active = await sessions.get_active_sessions(user.id)
    assert len(active) == 2
    active_ids = {row.id for row in active}
    assert older.id not in active_ids
    assert newer.id in active_ids

    revoked = await sessions.get_by_id(older.id)
    assert revoked is not None
    assert revoked.revoked_at is not None


async def test_max_active_sessions_allows_under_limit(
    user_factory, db_session
) -> None:
    settings = get_settings().model_copy(update={"max_active_sessions": 5})
    service = AuthService(db_session, settings=settings)
    user = await _verified_user(user_factory)
    await service.login(email=user.email, password=PASSWORD)
    await service.login(email=user.email, password=PASSWORD)
    sessions = SessionRepository(db_session)
    active = await sessions.get_active_sessions(user.id)
    assert len(active) == 2


# ---------------------------------------------------------------------------
# Negative security: user enumeration resistance
# ---------------------------------------------------------------------------


async def test_login_error_matches_for_unknown_email_and_wrong_password(
    user_factory, db_session
) -> None:
    """Unknown email and wrong password raise an identical generic message."""
    service = AuthService(db_session)
    user = await _verified_user(user_factory)
    with pytest.raises(UnauthorizedError) as unknown_exc:
        await service.login(email="nobody@example.com", password=PASSWORD)
    with pytest.raises(UnauthorizedError) as wrong_exc:
        await service.login(email=user.email, password="Wrong!password")
    assert unknown_exc.value.message == wrong_exc.value.message
