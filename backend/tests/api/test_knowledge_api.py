"""Knowledge base API tests (API_SPECIFICATION.md §23).

Covers the read-side document and chunk retrieval surface.
"""

from __future__ import annotations


def test_list_documents(api_client, seed_ids, auth_headers) -> None:
    """GET /knowledge/documents lists active indexed documents."""
    response = api_client.get(
        "/api/v1/knowledge/documents",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    doc = body["data"][0]
    assert doc["id"] == str(seed_ids["document_id"])
    assert doc["title"] == "Admissions Handbook 2025"
    assert doc["category"] == "admission"
    assert doc["status"] == "processed"
    assert doc["is_active"] is True


def test_get_document(api_client, seed_ids, auth_headers) -> None:
    """GET /knowledge/documents/{id} returns document metadata."""
    response = api_client.get(
        f"/api/v1/knowledge/documents/{seed_ids['document_id']}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_path"] == "knowledge/admission/handbook-2025.md"
    assert data["chunk_count"] == 1


def test_get_document_sources(api_client, seed_ids, auth_headers) -> None:
    """GET /knowledge/documents/{id}/sources returns the chunks."""
    response = api_client.get(
        f"/api/v1/knowledge/documents/{seed_ids['document_id']}/sources",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(seed_ids["chunk_id"])
    assert items[0]["chunk_index"] == 0
    assert items[0]["chunk_text"] == "Applications open in March."


def test_get_missing_document_is_404(api_client, seed_ids, auth_headers) -> None:
    """A nonexistent document yields a 404 envelope."""
    missing = "00000000-0000-0000-0000-0000000000ff"
    response = api_client.get(
        f"/api/v1/knowledge/documents/{missing}",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_documents_require_auth(api_client) -> None:
    """Knowledge reads require the owner-context header (401)."""
    response = api_client.get("/api/v1/knowledge/documents")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH001"
