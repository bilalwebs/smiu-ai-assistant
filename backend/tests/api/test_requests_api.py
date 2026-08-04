"""Request API tests (API_SPECIFICATION.md §18).

Covers owner-scoped listing, creation, detail, updates, soft-delete, status
transitions, and the append-only timeline.
"""

from __future__ import annotations


def test_list_requests_is_owner_scoped(api_client, seed_ids, auth_headers) -> None:
    """GET /requests returns only the acting user's requests with pagination."""
    response = api_client.get(
        "/api/v1/requests", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]
    assert len(items) == 3
    assert {item["status"] for item in items} == {"draft", "submitted", "resolved"}
    assert all(item["user_id"] == str(seed_ids["owner_user_id"]) for item in items)
    pagination = body["meta"]["pagination"]
    assert pagination["total"] == 3
    assert pagination["page"] == 1
    assert pagination["limit"] == 20


def test_list_requests_filters_by_status(api_client, seed_ids, auth_headers) -> None:
    """GET /requests?request_status=draft narrows the result set."""
    response = api_client.get(
        "/api/v1/requests",
        params={"request_status": "draft"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(seed_ids["draft_request_id"])


def test_create_request_returns_201(api_client, seed_ids, auth_headers) -> None:
    """POST /requests creates an owned draft request."""
    response = api_client.post(
        "/api/v1/requests",
        json={
            "request_type": "admission",
            "title": "Certificate request",
            "department_id": str(seed_ids["department_id"]),
        },
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_id"] == str(seed_ids["owner_user_id"])
    assert data["status"] == "draft"
    assert data["request_no"].startswith("REQ-")
    assert data["department_id"] == str(seed_ids["department_id"])


def test_create_request_rejects_terminal_status(api_client, seed_ids, auth_headers) -> None:
    """Creating a request in a non-initial status is rejected (422)."""
    response = api_client.post(
        "/api/v1/requests",
        json={"request_type": "general", "title": "Bad status", "status": "resolved"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL001"


def test_get_request_detail(api_client, seed_ids, auth_headers) -> None:
    """GET /requests/{id} returns the owned request's details."""
    response = api_client.get(
        f"/api/v1/requests/{seed_ids['submitted_request_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(seed_ids["submitted_request_id"])
    assert data["request_no"] == "REQ-000002"
    assert data["priority"] == "high"


def test_get_foreign_request_is_forbidden(api_client, seed_ids, auth_headers) -> None:
    """A request owned by another user is not exposed (403)."""
    response = api_client.get(
        f"/api/v1/requests/{seed_ids['other_request_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_get_missing_request_is_404(api_client, seed_ids, auth_headers) -> None:
    """A nonexistent request yields a 404 envelope."""
    missing = "00000000-0000-0000-0000-0000000000ff"
    response = api_client.get(
        f"/api/v1/requests/{missing}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_patch_request_updates_fields(api_client, seed_ids, auth_headers) -> None:
    """PATCH /requests/{id} updates editable fields of an owned request."""
    response = api_client.patch(
        f"/api/v1/requests/{seed_ids['draft_request_id']}",
        json={"title": "Updated title", "priority": "high"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Updated title"
    assert data["priority"] == "high"


def test_delete_request_soft_deletes(api_client, seed_ids, auth_headers) -> None:
    """DELETE /requests/{id} soft-deletes and hides the request afterwards."""
    response = api_client.delete(
        f"/api/v1/requests/{seed_ids['draft_request_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(seed_ids["draft_request_id"])

    detail = api_client.get(
        f"/api/v1/requests/{seed_ids['draft_request_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert detail.status_code == 404


def test_submit_request_transitions_draft(api_client, seed_ids, auth_headers) -> None:
    """POST /requests/{id}/submit moves a draft to submitted."""
    response = api_client.post(
        f"/api/v1/requests/{seed_ids['draft_request_id']}/submit",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "submitted"


def test_resolve_and_close_flow(api_client, seed_ids, auth_headers) -> None:
    """Resolved requests can be closed through the status machine."""
    resolve = api_client.post(
        f"/api/v1/requests/{seed_ids['submitted_request_id']}/resolve",
        json={"status": "resolved", "resolution_notes": "Handled."},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert resolve.status_code == 200
    assert resolve.json()["data"]["status"] == "resolved"

    close = api_client.post(
        f"/api/v1/requests/{seed_ids['submitted_request_id']}/close",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert close.status_code == 200
    assert close.json()["data"]["status"] == "closed"


def test_reject_requires_reason(api_client, seed_ids, auth_headers) -> None:
    """Rejecting a request with an empty reason is rejected (422)."""
    response = api_client.post(
        f"/api/v1/requests/{seed_ids['submitted_request_id']}/reject",
        json={"status": "rejected", "rejection_reason": ""},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL001"


def test_invalid_transition_rejected(api_client, seed_ids, auth_headers) -> None:
    """Resolving a draft (no allowed transition) is rejected (422)."""
    response = api_client.post(
        f"/api/v1/requests/{seed_ids['draft_request_id']}/resolve",
        json={"status": "resolved"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL001"


def test_timeline_is_owner_scoped(api_client, seed_ids, auth_headers) -> None:
    """GET /requests/{id}/timeline returns the append-only events."""
    response = api_client.get(
        f"/api/v1/requests/{seed_ids['submitted_request_id']}/timeline",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"] == []

    foreign = api_client.get(
        f"/api/v1/requests/{seed_ids['other_request_id']}/timeline",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert foreign.status_code == 403
