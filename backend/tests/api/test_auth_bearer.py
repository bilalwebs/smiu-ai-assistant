"""Bearer JWT authentication tests (API_SPECIFICATION.md §3, §5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config.settings import get_settings
from app.core.security.jwt import (
    CLAIM_TYPE,
    TOKEN_TYPE_ACCESS,
    create_access_token,
    create_email_verification_token,
)
from app.models import UserRole


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_bearer_returns_401(api_client, seed_ids) -> None:
    response = api_client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_malformed_scheme_returns_401(api_client, seed_ids) -> None:
    response = api_client.get(
        "/api/v1/users/me", headers={"Authorization": "Basic abc123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_garbage_token_returns_401(api_client, seed_ids) -> None:
    response = api_client.get("/api/v1/users/me", headers=_bearer("not-a-jwt"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_expired_token_returns_401(api_client, seed_ids) -> None:
    """An access token past its expiry is rejected (API_SPECIFICATION.md §5.3)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(seed_ids["owner_user_id"]),
        "jti": uuid.uuid4().hex,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        CLAIM_TYPE: TOKEN_TYPE_ACCESS,
        "role": UserRole.STUDENT.value,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    response = api_client.get("/api/v1/users/me", headers=_bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_wrong_purpose_token_returns_401(api_client, seed_ids) -> None:
    """A non-access token cannot authenticate a protected route."""
    settings = get_settings()
    verification = create_email_verification_token(
        subject=str(seed_ids["owner_user_id"]), settings=settings
    )
    response = api_client.get("/api/v1/users/me", headers=_bearer(verification))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_valid_bearer_grants_owner_context(api_client, seed_ids) -> None:
    """A verified access token resolves the acting user for protected routes."""
    settings = get_settings()
    token = create_access_token(
        subject=str(seed_ids["owner_user_id"]),
        role=UserRole.STUDENT.value,
        settings=settings,
    )
    response = api_client.get("/api/v1/users/me", headers=_bearer(token))
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(seed_ids["owner_user_id"])


def test_protected_routes_reject_unauthenticated(api_client) -> None:
    """Every non-public route rejects missing credentials (§4.4)."""
    for path in (
        "/api/v1/requests",
        "/api/v1/notifications",
        "/api/v1/conversations",
        "/api/v1/students/me",
    ):
        response = api_client.get(path)
        assert response.status_code == 401
