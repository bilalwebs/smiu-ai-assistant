"""Notification API tests (API_SPECIFICATION.md §19).

Covers the owner-scoped activity feed, read-marking, and soft-delete.
"""

from __future__ import annotations


def test_list_notifications(api_client, seed_ids, auth_headers) -> None:
    """GET /notifications returns the acting user's notifications."""
    response = api_client.get(
        "/api/v1/notifications", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 2
    assert body["meta"]["pagination"]["total"] == 2


def test_list_notifications_filters_by_read(api_client, seed_ids, auth_headers) -> None:
    """GET /notifications?read=true filters to read notifications only."""
    unread = api_client.get(
        "/api/v1/notifications",
        params={"read": "false"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert unread.status_code == 200
    assert [item["id"] for item in unread.json()["data"]] == [
        str(seed_ids["notif_unread_id"])
    ]

    read = api_client.get(
        "/api/v1/notifications",
        params={"read": "true"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert read.status_code == 200
    assert [item["id"] for item in read.json()["data"]] == [
        str(seed_ids["notif_read_id"])
    ]


def test_unread_count(api_client, seed_ids, auth_headers) -> None:
    """GET /notifications/unread-count reports the owner's unread total."""
    response = api_client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"unread": 1}


def test_mark_read(api_client, seed_ids, auth_headers) -> None:
    """POST /notifications/{id}/read marks an unread notification read."""
    response = api_client.post(
        f"/api/v1/notifications/{seed_ids['notif_unread_id']}/read",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(seed_ids["notif_unread_id"])
    assert data["read_at"] is not None

    count = api_client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert count.json()["data"] == {"unread": 0}


def test_mark_read_twice_is_rejected(api_client, seed_ids, auth_headers) -> None:
    """Marking an already-read notification is rejected (422)."""
    response = api_client.post(
        f"/api/v1/notifications/{seed_ids['notif_read_id']}/read",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL001"


def test_read_all(api_client, seed_ids, auth_headers) -> None:
    """POST /notifications/read-all clears the owner's unread set."""
    response = api_client.post(
        "/api/v1/notifications/read-all",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"marked": 1}

    count = api_client.get(
        "/api/v1/notifications/unread-count",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert count.json()["data"] == {"unread": 0}


def test_delete_notification(api_client, seed_ids, auth_headers) -> None:
    """DELETE /notifications/{id} soft-deletes and hides the notification."""
    response = api_client.delete(
        f"/api/v1/notifications/{seed_ids['notif_unread_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200

    listing = api_client.get(
        "/api/v1/notifications", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert listing.json()["meta"]["pagination"]["total"] == 1


def test_foreign_notification_is_forbidden(api_client, seed_ids, auth_headers) -> None:
    """An other-user notification is not markable (403)."""
    response = api_client.post(
        f"/api/v1/notifications/{seed_ids['notif_unread_id']}/read",
        headers=auth_headers(seed_ids["other_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"
