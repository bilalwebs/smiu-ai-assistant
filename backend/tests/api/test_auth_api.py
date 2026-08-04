"""Auth API contract tests (API_SPECIFICATION.md §3.3)."""

from __future__ import annotations

from app.config.settings import get_settings
from app.core.security.jwt import create_email_verification_token

REGISTER_PAYLOAD = {
    "email": "fresh.student@example.com",
    "password": "Sup3r!secure",
    "full_name": "Fresh Student",
    "enrollment_no": "SM-2026-001",
    "program_name": "BS Computer Science",
}


def _register_and_verify(api_client) -> str:
    """Register a student and activate it via a signed verification token."""
    response = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    user_id = response.json()["data"]["id"]
    token = create_email_verification_token(
        subject=user_id, settings=get_settings()
    )
    verified = api_client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    return user_id


def test_register_returns_201_pending_user(api_client) -> None:
    """POST /auth/register creates a pending student in the envelope."""
    response = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["email"] == REGISTER_PAYLOAD["email"]
    assert data["role"] == "student"
    assert data["status"] == "pending"
    assert data["email_verified_at"] is None
    assert body["meta"]["request_id"]


def test_register_duplicate_email_returns_409(api_client) -> None:
    """Duplicate registration is rejected with a conflict envelope."""
    first = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert first.status_code == 201
    second = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert second.status_code == 409
    body = second.json()
    assert body["success"] is False
    assert body["error"]["code"] == "REQ004"


def test_register_weak_password_returns_422(api_client) -> None:
    """A password violating the strength policy is rejected at the schema."""
    payload = {**REGISTER_PAYLOAD, "password": "short"}
    response = api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VAL002"
    assert any(detail["field"] == "password" for detail in body["error"]["details"])


def test_verify_email_activates_account(api_client) -> None:
    """A signed verification token activates the pending account."""
    response = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    user_id = response.json()["data"]["id"]
    token = create_email_verification_token(subject=user_id, settings=get_settings())
    verified = api_client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    data = verified.json()["data"]
    assert data["id"] == user_id
    assert data["status"] == "active"
    assert data["email_verified_at"] is not None


def test_verify_email_invalid_token_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/verify-email", json={"token": "garbage-token"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "AUTH001"


def test_login_returns_token_pair(api_client) -> None:
    """Login with a verified active user returns access + refresh tokens."""
    _register_and_verify(api_client)
    login = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        },
    )
    assert login.status_code == 200
    data = login.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] == 3600
    assert data["refresh_expires_in"] == 7 * 24 * 3600
    assert data["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert data["user"]["status"] == "active"


def test_login_remember_me_extends_refresh_lifetime(api_client) -> None:
    """remember_me=true extends the refresh-token lifetime to 30 days."""
    _register_and_verify(api_client)
    login = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
            "remember_me": True,
        },
    )
    assert login.status_code == 200
    assert login.json()["data"]["refresh_expires_in"] == 30 * 24 * 3600


def test_login_unverified_user_returns_403(api_client) -> None:
    """An unverified account cannot log in (verification is mandatory)."""
    api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        },
    )
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "AUTH003"


def test_login_wrong_password_returns_401(api_client) -> None:
    _register_and_verify(api_client)
    response = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": "Wrong!password",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_login_unknown_email_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Sup3r!secure"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_login_missing_fields_returns_422(api_client) -> None:
    response = api_client.post("/api/v1/auth/login", json={"email": "x@example.com"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL002"


# -- refresh / logout -------------------------------------------------------


def _login_credentials() -> dict[str, str]:
    return {
        "email": REGISTER_PAYLOAD["email"],
        "password": REGISTER_PAYLOAD["password"],
    }


def test_refresh_rotates_token_pair(api_client) -> None:
    """POST /auth/refresh rotates into a new pair; the old token is a replay."""
    _register_and_verify(api_client)
    login = api_client.post("/api/v1/auth/login", json=_login_credentials())
    old_access = login.json()["data"]["access_token"]
    old_refresh = login.json()["data"]["refresh_token"]

    refreshed = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refreshed.status_code == 200
    data = refreshed.json()["data"]
    assert data["access_token"] != old_access
    assert data["refresh_token"] != old_refresh
    assert data["expires_in"] == 3600
    assert data["refresh_expires_in"] == 7 * 24 * 3600
    assert data["user"]["email"] == REGISTER_PAYLOAD["email"]

    replayed = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "AUTH001"


def test_refresh_invalid_token_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "garbage-refresh"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_refresh_missing_field_returns_422(api_client) -> None:
    response = api_client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL002"


def test_logout_revokes_session(api_client) -> None:
    """POST /auth/logout revokes the session so its refresh token stops working."""
    _register_and_verify(api_client)
    login = api_client.post("/api/v1/auth/login", json=_login_credentials())
    refresh_token = login.json()["data"]["refresh_token"]

    logged_out = api_client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logged_out.status_code == 200
    assert logged_out.json()["data"] is None

    refresh_after = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after.status_code == 401


def test_logout_unknown_token_is_idempotent(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/logout", json={"refresh_token": "garbage-refresh"}
    )
    assert response.status_code == 200


def test_logout_all_revokes_every_session(api_client) -> None:
    """POST /auth/logout-all revokes every session of the token's owner."""
    _register_and_verify(api_client)
    first = api_client.post("/api/v1/auth/login", json=_login_credentials())
    second = api_client.post("/api/v1/auth/login", json=_login_credentials())
    first_refresh = first.json()["data"]["refresh_token"]
    second_refresh = second.json()["data"]["refresh_token"]

    logged_out = api_client.post(
        "/api/v1/auth/logout-all", json={"refresh_token": first_refresh}
    )
    assert logged_out.status_code == 200
    assert logged_out.json()["data"] == {"revoked": 2}

    for token in (first_refresh, second_refresh):
        response = api_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": token}
        )
        assert response.status_code == 401


def test_logout_all_unknown_token_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/logout-all", json={"refresh_token": "garbage-refresh"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


# -- forgot password ---------------------------------------------------------


def test_forgot_password_returns_generic_success(api_client) -> None:
    """POST /auth/forgot-password always returns a generic message (no enumeration)."""
    response = api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "password reset link" in body["data"]["message"].lower()


def test_forgot_password_for_existing_user_returns_same_response(api_client) -> None:
    """The response is identical whether or not the email exists."""
    _register_and_verify(api_client)
    response = api_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": REGISTER_PAYLOAD["email"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "password reset link" in body["data"]["message"].lower()


def test_forgot_password_missing_email_returns_422(api_client) -> None:
    response = api_client.post("/api/v1/auth/forgot-password", json={})
    assert response.status_code == 422


# -- reset password ----------------------------------------------------------


def test_reset_password_invalid_token_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "garbage-token",
            "password": "N3w!Password",
            "confirm_password": "N3w!Password",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_reset_password_weak_password_returns_422(api_client) -> None:
    """A password that violates the strength policy is rejected at schema level."""
    response = api_client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "some-token",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert response.status_code == 422


def test_reset_password_mismatched_passwords_returns_422(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "some-token",
            "password": "N3w!Password",
            "confirm_password": "D1fferent!",
        },
    )
    assert response.status_code == 422


def test_reset_password_missing_fields_returns_422(api_client) -> None:
    response = api_client.post("/api/v1/auth/reset-password", json={})
    assert response.status_code == 422


# -- change password ---------------------------------------------------------


def test_change_password_returns_401_without_auth(api_client) -> None:
    response = api_client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "Sup3r!secure",
            "new_password": "N3w!Password",
        },
    )
    assert response.status_code == 401


def test_change_password_weak_new_password_returns_422(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "Sup3r!secure",
            "new_password": "short",
        },
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422


def test_change_password_missing_fields_returns_422(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.post(
        "/api/v1/users/me/change-password",
        json={},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
