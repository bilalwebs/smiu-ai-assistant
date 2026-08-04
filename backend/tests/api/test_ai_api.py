"""AI API tests (API_SPECIFICATION.md §21).

Covers citation sources per message and feedback submission/triage.
"""

from __future__ import annotations


def test_get_sources_for_message(api_client, seed_ids, auth_headers) -> None:
    """GET /ai/sources/{message_id} returns the message's citations."""
    response = api_client.get(
        f"/api/v1/ai/sources/{seed_ids['message_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    source = items[0]
    assert source["message_id"] == str(seed_ids["message_id"])
    assert source["source_type"] == "rag"
    assert source["source_title"] == "Admissions Handbook 2025"
    assert source["relevance_score"] == 0.93


def test_get_sources_foreign_message_is_404(api_client, seed_ids, auth_headers) -> None:
    """Citations on another user's message are not exposed (404)."""
    response = api_client.get(
        f"/api/v1/ai/sources/{seed_ids['message_id']}",
        headers=auth_headers(seed_ids["other_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_submit_feedback(api_client, seed_ids, auth_headers) -> None:
    """POST /ai/feedback submits a rating on the user's own message (201)."""
    response = api_client.post(
        "/api/v1/ai/feedback",
        json={
            "message_id": str(seed_ids["message_id"]),
            "conversation_id": str(seed_ids["conversation_id"]),
            "feedback_type": "comment",
            "comment": "Very helpful.",
        },
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_id"] == str(seed_ids["owner_user_id"])
    assert data["feedback_type"] == "comment"
    assert data["comment"] == "Very helpful."
    assert data["status"] == "open"


def test_submit_duplicate_feedback_is_conflict(api_client, seed_ids, auth_headers) -> None:
    """A second rating of the same type on a message is a conflict (409)."""
    payload = {
        "message_id": str(seed_ids["message_id"]),
        "conversation_id": str(seed_ids["conversation_id"]),
        "feedback_type": "rating",
        "rating": 4,
    }
    response = api_client.post(
        "/api/v1/ai/feedback",
        json=payload,
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REQ004"


def test_submit_feedback_foreign_message_is_404(api_client, seed_ids, auth_headers) -> None:
    """Feedback cannot reference another user's message (404)."""
    response = api_client.post(
        "/api/v1/ai/feedback",
        json={
            "message_id": str(seed_ids["message_id"]),
            "feedback_type": "comment",
            "comment": "nope",
        },
        headers=auth_headers(seed_ids["other_user_id"]),
    )
    assert response.status_code == 404


def test_update_feedback_status(api_client, seed_ids, auth_headers) -> None:
    """PATCH /ai/feedback/{id}/status transitions through triage states."""
    response = api_client.patch(
        f"/api/v1/ai/feedback/{seed_ids['feedback_id']}/status",
        json={"status": "resolved", "resolution_notes": "Handled in review."},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "resolved"
    assert data["resolution_notes"] == "Handled in review."
