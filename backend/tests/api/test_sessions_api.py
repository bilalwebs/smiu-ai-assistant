"""Session-management API tests (API_SPECIFICATION.md §17; DATABASE_DESIGN.md §25)."""

from __future__ import annotations

import uuid

from app.config.settings import get_settings
from app.core.security.jwt import create_email_verification_token

REGISTER_PAYLOAD = {
    "email": "session.student@example.com",
    "password": "Sup3r!secure",
    "full_name": "Session Student",
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


def _login(api_client) -> dict:
    response = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_list_sessions_returns_active_sessions(api_client) -> None:
    """GET /users/me/sessions lists the acting user's live sessions."""
    _register_and_verify(api_client)
    login = _login(api_client)
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = api_client.get("/api/v1/users/me/sessions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["pagination"]["total"] == 1
    session = body["data"][0]
    assert session["id"]
    assert session["created_at"]
    assert session["expires_at"]


def test_list_sessions_is_owner_scoped(api_client) -> None:
    """A user only ever sees their own sessions."""
    _register_and_verify(api_client)
    owner_login = _login(api_client)
    owner_headers = {"Authorization": f"Bearer {owner_login['access_token']}"}

    other_payload = {**REGISTER_PAYLOAD, "email": "other.session@example.com"}
    response = api_client.post("/api/v1/auth/register", json=other_payload)
    other_id = response.json()["data"]["id"]
    other_token = create_email_verification_token(
        subject=other_id, settings=get_settings()
    )
    api_client.post("/api/v1/auth/verify-email", json={"token": other_token})
    other_login = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": other_payload["email"],
            "password": other_payload["password"],
        },
    )
    assert other_login.status_code == 200

    owner_sessions = api_client.get(
        "/api/v1/users/me/sessions", headers=owner_headers
    )
    assert owner_sessions.status_code == 200
    assert owner_sessions.json()["meta"]["pagination"]["total"] == 1


def test_revoke_session_terminates_refresh(api_client) -> None:
    """DELETE /users/me/sessions/{id} revokes the session's refresh token."""
    _register_and_verify(api_client)
    login = _login(api_client)
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    listed = api_client.get("/api/v1/users/me/sessions", headers=headers)
    session_id = listed.json()["data"][0]["id"]

    revoked = api_client.delete(
        f"/api/v1/users/me/sessions/{session_id}", headers=headers
    )
    assert revoked.status_code == 200
    assert revoked.json()["data"]["id"] == session_id

    refresh_after = api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert refresh_after.status_code == 401


def test_revoke_session_repeat_is_idempotent(api_client) -> None:
    """A second revoke of the same session still succeeds."""
    _register_and_verify(api_client)
    login = _login(api_client)
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    listed = api_client.get("/api/v1/users/me/sessions", headers=headers)
    session_id = listed.json()["data"][0]["id"]

    first = api_client.delete(
        f"/api/v1/users/me/sessions/{session_id}", headers=headers
    )
    second = api_client.delete(
        f"/api/v1/users/me/sessions/{session_id}", headers=headers
    )
    assert first.status_code == 200
    assert second.status_code == 200


def test_revoke_foreign_session_is_forbidden(api_client) -> None:
    """Revoking another user's session is forbidden."""
    _register_and_verify(api_client)
    owner_login = _login(api_client)
    owner_headers = {"Authorization": f"Bearer {owner_login['access_token']}"}
    listed = api_client.get("/api/v1/users/me/sessions", headers=owner_headers)
    session_id = listed.json()["data"][0]["id"]

    other_payload = {**REGISTER_PAYLOAD, "email": "other.owner@example.com"}
    response = api_client.post("/api/v1/auth/register", json=other_payload)
    other_user_id = response.json()["data"]["id"]
    other_token = create_email_verification_token(
        subject=other_user_id, settings=get_settings()
    )
    api_client.post("/api/v1/auth/verify-email", json={"token": other_token})
    other_login = api_client.post(
        "/api/v1/auth/login",
        json={
            "email": other_payload["email"],
            "password": other_payload["password"],
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['data']['access_token']}"
    }

    response = api_client.delete(
        f"/api/v1/users/me/sessions/{session_id}", headers=other_headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_revoke_missing_session_is_404(api_client) -> None:
    """Revoking a non-existent session returns 404."""
    _register_and_verify(api_client)
    login = _login(api_client)
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = api_client.delete(
        f"/api/v1/users/me/sessions/{uuid.uuid4()}", headers=headers
    )
    assert response.status_code == 404


def test_sessions_require_authentication(api_client) -> None:
    """Session endpoints are protected routes (§4.4)."""
    response = api_client.get("/api/v1/users/me/sessions")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"
