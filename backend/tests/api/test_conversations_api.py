"""Conversation API tests (API_SPECIFICATION.md §20, §22).

Covers conversation lifecycle: create, list, detail, update, archive/restore,
and soft-delete, all owner-scoped.
"""

from __future__ import annotations


def test_create_conversation(api_client, seed_ids, auth_headers) -> None:
    """POST /conversations creates an active conversation for the user."""
    response = api_client.post(
        "/api/v1/conversations",
        json={
            "title": "New chat",
            "department_id": str(seed_ids["department_id"]),
            "first_message": "Hello",
        },
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_id"] == str(seed_ids["owner_user_id"])
    assert data["status"] == "active"
    assert data["message_count"] == 1


def test_list_conversations_is_owner_scoped(api_client, seed_ids, auth_headers) -> None:
    """GET /conversations returns only the acting user's conversations."""
    response = api_client.get(
        "/api/v1/conversations", headers=auth_headers(seed_ids["owner_user_id"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["pagination"]["total"] == 1
    assert body["data"][0]["id"] == str(seed_ids["conversation_id"])


def test_get_conversation_detail(api_client, seed_ids, auth_headers) -> None:
    """GET /conversations/{id} returns the owned conversation."""
    response = api_client.get(
        f"/api/v1/conversations/{seed_ids['conversation_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Admission help"
    assert data["status"] == "active"
    assert data["current_agent"] == "admission"
    assert data["message_count"] == 1


def test_get_foreign_conversation_is_forbidden(api_client, seed_ids, auth_headers) -> None:
    """An other-user conversation is not exposed (403)."""
    response = api_client.get(
        f"/api/v1/conversations/{seed_ids['other_conversation_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH003"


def test_patch_conversation(api_client, seed_ids, auth_headers) -> None:
    """PATCH /conversations/{id} updates title/summary metadata."""
    response = api_client.patch(
        f"/api/v1/conversations/{seed_ids['conversation_id']}",
        json={"title": "Renamed chat", "summary": "Updated summary"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Renamed chat"
    assert data["summary"] == "Updated summary"


def test_archive_and_restore_conversation(api_client, seed_ids, auth_headers) -> None:
    """Archive then restore flips conversation status."""
    archived = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/archive",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"

    restored = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/restore",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["status"] == "active"


def test_archive_non_active_is_rejected(api_client, seed_ids, auth_headers) -> None:
    """Archiving a non-active conversation is rejected (422)."""
    api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/archive",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/archive",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL001"


def test_delete_conversation(api_client, seed_ids, auth_headers) -> None:
    """DELETE /conversations/{id} soft-deletes and hides the conversation."""
    response = api_client.delete(
        f"/api/v1/conversations/{seed_ids['conversation_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200

    detail = api_client.get(
        f"/api/v1/conversations/{seed_ids['conversation_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert detail.status_code == 404
