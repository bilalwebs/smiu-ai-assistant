"""User API tests (API_SPECIFICATION.md §17).

Covers the owner-scoped profile endpoints and the auth-stub gate.
"""

from __future__ import annotations


def test_get_me_returns_owner_profile(api_client, seed_ids, auth_headers) -> None:
    """GET /users/me returns the acting user's profile in the success envelope."""
    response = api_client.get(
        "/api/v1/users/me", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == str(seed_ids["owner_user_id"])
    assert data["email"] == "owner@example.com"
    assert data["full_name"] == "Owner Student"
    assert data["role"] == "student"
    assert data["status"] == "active"
    assert body["meta"]["request_id"]
    assert body["meta"]["timestamp"].endswith("Z")


def test_get_me_requires_auth(api_client) -> None:
    """Missing owner-context header is rejected with the AUTH001 envelope."""
    response = api_client.get("/api/v1/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AUTH001"
    assert body["meta"]["request_id"]


def test_get_me_rejects_malformed_user_id(api_client) -> None:
    """A non-UUID owner-context header is rejected with 401."""
    response = api_client.get(
        "/api/v1/users/me", headers={"X-User-Id": "not-a-uuid"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"


def test_update_me_updates_profile(api_client, seed_ids, auth_headers) -> None:
    """PATCH /users/me applies the editable profile fields."""
    response = api_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Updated Name", "phone": "+92-300-0000000"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "+92-300-0000000"


def test_update_me_validates_payload(api_client, seed_ids, auth_headers) -> None:
    """Invalid profile payloads are rejected with a VAL002 envelope."""
    response = api_client.patch(
        "/api/v1/users/me",
        json={"full_name": ""},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VAL002"
    assert body["error"]["details"]
