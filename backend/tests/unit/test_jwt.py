"""JWT utility tests (API_SPECIFICATION.md §5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from app.config.settings import get_settings
from app.core.security.jwt import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_EMAIL_VERIFICATION,
    create_access_token,
    create_email_verification_token,
    decode_token,
    generate_refresh_token,
    hash_refresh_token,
)


def _settings():
    return get_settings()


def test_access_token_round_trip() -> None:
    settings = _settings()
    token = create_access_token(subject="user-1", role="student", settings=settings)
    claims = decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)
    assert claims.subject == "user-1"
    assert claims.role == "student"
    assert claims.token_type == TOKEN_TYPE_ACCESS
    assert claims.jti
    assert claims.expires_at > datetime.now(UTC)
    assert claims.expires_at <= datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes + 1
    )


def test_access_token_carries_supplied_jti() -> None:
    settings = _settings()
    token = create_access_token(
        subject="user-1", role="admin", settings=settings, jti="session-jti"
    )
    claims = decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)
    assert claims.jti == "session-jti"
    assert claims.role == "admin"


def test_email_verification_token_round_trip() -> None:
    settings = _settings()
    token = create_email_verification_token(subject="user-1", settings=settings)
    claims = decode_token(
        token=token,
        expected_type=TOKEN_TYPE_EMAIL_VERIFICATION,
        settings=settings,
    )
    assert claims.subject == "user-1"
    assert claims.token_type == TOKEN_TYPE_EMAIL_VERIFICATION
    assert claims.role is None


def test_access_token_is_rejected_as_verification_token() -> None:
    settings = _settings()
    token = create_access_token(subject="user-1", role="student", settings=settings)
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(
            token=token,
            expected_type=TOKEN_TYPE_EMAIL_VERIFICATION,
            settings=settings,
        )


def test_token_signed_with_other_secret_is_rejected() -> None:
    settings = _settings()
    foreign = settings.model_copy(update={"jwt_secret": "attacker-secret"})
    token = create_access_token(subject="user-1", role="student", settings=foreign)
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)


def test_expired_token_is_rejected() -> None:
    settings = _settings()
    now = datetime.now(UTC)
    payload = {
        "sub": "user-1",
        "jti": "jti",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "typ": TOKEN_TYPE_ACCESS,
    }
    token = pyjwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(token=token, expected_type=TOKEN_TYPE_ACCESS, settings=settings)


def test_garbage_token_is_rejected() -> None:
    settings = _settings()
    with pytest.raises(pyjwt.PyJWTError):
        decode_token(
            token="not-a-jwt", expected_type=TOKEN_TYPE_ACCESS, settings=settings
        )


def test_refresh_token_is_random_and_hash_is_stable() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()
    assert first != second
    assert len(hash_refresh_token(first)) == 64
    assert hash_refresh_token(first) == hash_refresh_token(first)
    assert hash_refresh_token(first) != hash_refresh_token(second)
