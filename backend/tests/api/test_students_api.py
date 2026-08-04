"""Student API tests (API_SPECIFICATION.md §15).

Covers the owner-scoped academic profile and dashboard aggregates.
"""

from __future__ import annotations


def test_get_me_returns_student_profile(api_client, seed_ids, auth_headers) -> None:
    """GET /students/me returns the acting user's academic profile."""
    response = api_client.get(
        "/api/v1/students/me", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == str(seed_ids["student_id"])
    assert data["user_id"] == str(seed_ids["owner_user_id"])
    assert data["enrollment_no"] == "SM-2024-001"
    assert data["status"] == "active"


def test_get_me_404_without_profile(api_client, seed_ids, auth_headers) -> None:
    """A user without a student profile gets a 404, not the other user's row."""
    response = api_client.get(
        "/api/v1/students/me", headers=auth_headers(seed_ids["other_user_id"])
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_update_me_updates_profile(api_client, seed_ids, auth_headers) -> None:
    """PATCH /students/me applies editable academic fields."""
    response = api_client.patch(
        "/api/v1/students/me",
        json={"current_semester": 4, "phone": "+92-300-1234567"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_semester"] == 4
    assert data["phone"] == "+92-300-1234567"


def test_update_me_rejects_invalid_semester(api_client, seed_ids, auth_headers) -> None:
    """Out-of-range semester values fail schema validation (422)."""
    response = api_client.patch(
        "/api/v1/students/me",
        json={"current_semester": 99},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL002"


def test_dashboard_counts_are_owner_scoped(api_client, seed_ids, auth_headers) -> None:
    """Dashboard aggregates reflect only the acting user's own data."""
    response = api_client.get(
        "/api/v1/students/me/dashboard",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["active_requests"] == 1
    assert data["pending_requests"] == 1
    assert data["resolved_requests"] == 1
    assert data["unread_notifications"] == 1
