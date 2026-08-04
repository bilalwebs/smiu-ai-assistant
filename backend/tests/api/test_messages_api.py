"""Chat message API tests (API_SPECIFICATION.md §20).

Covers message send and history within an owner-scoped conversation.
"""

from __future__ import annotations


def test_send_message(api_client, seed_ids, auth_headers) -> None:
    """POST /conversations/{id}/messages appends a user message (201)."""
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/messages",
        json={"content": "When is the deadline?"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == "user"
    assert data["content"] == "When is the deadline?"
    assert data["status"] == "completed"
    assert data["conversation_id"] == str(seed_ids["conversation_id"])


def test_get_message_history(api_client, seed_ids, auth_headers) -> None:
    """GET /conversations/{id}/messages returns messages chronologically."""
    response = api_client.get(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/messages",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(seed_ids["message_id"])
    assert items[0]["content"] == "How do I apply?"


def test_send_message_foreign_conversation_is_404(api_client, seed_ids, auth_headers) -> None:
    """Messages on an other-user conversation are not exposed (404)."""
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['other_conversation_id']}/messages",
        json={"content": "hi"},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_send_message_requires_content(api_client, seed_ids, auth_headers) -> None:
    """Empty message content fails schema validation (422)."""
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/messages",
        json={"content": ""},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VAL002"
