"""Document upload API tests (API_SPECIFICATION.md).

Tests for user document upload: standalone upload, conversation attachment,
list by conversation, and ownership enforcement.
"""

from __future__ import annotations

import io
import uuid

from tests.api.conftest import OTHER_CONVERSATION_ID, OWNER_USER_ID


_VALID_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>\n"
    b"stream\n"
    b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000266 00000 n \n"
    b"0000000360 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n441\n%%EOF\n"
)


def test_standalone_upload_returns_201(api_client, seed_ids, auth_headers) -> None:
    response = api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    doc = body["data"]["document"]
    assert doc["original_filename"] == "test.pdf"
    assert doc["status"] == "processed"
    assert doc["user_id"] == str(seed_ids["owner_user_id"])
    uuid.UUID(doc["id"])  # valid UUID


def test_standalone_upload_rejects_unauthed(api_client, seed_ids) -> None:
    response = api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
    )
    assert response.status_code in (401, 403)


def test_standalone_upload_rejects_non_pdf(api_client, seed_ids, auth_headers) -> None:
    response = api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", io.BytesIO(b"not pdf"), "text/plain")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False


def test_conversation_attachment_upload_returns_201(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/attachments",
        files={"file": ("attach.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    doc = body["data"]["document"]
    assert doc["original_filename"] == "attach.pdf"


def test_conversation_attachment_rejects_other_users_conversation(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.post(
        f"/api/v1/conversations/{seed_ids['other_conversation_id']}/attachments",
        files={"file": ("bad.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False


def test_list_attachments_returns_linked_docs_only(
    api_client, seed_ids, auth_headers
) -> None:
    # Upload standalone (no conversation link)
    resp1 = api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("standalone.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    standalone_id = resp1.json()["data"]["document"]["id"]

    # List attachments for conversation — should not include the standalone doc
    response = api_client.get(
        f"/api/v1/conversations/{seed_ids['conversation_id']}/attachments",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    body = response.json()
    doc_ids = [d["id"] for d in body["data"]]
    assert standalone_id not in doc_ids


def test_list_attachments_excludes_other_users_conversations(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.get(
        f"/api/v1/conversations/{seed_ids['other_conversation_id']}/attachments",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 403


def test_document_not_in_knowledge_faiss(
    api_client, seed_ids, auth_headers
) -> None:
    """User uploads must NOT appear in knowledge/FAISS index."""
    # Upload a document
    api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("userdoc.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    # List knowledge documents — should be unchanged (only seeded docs)
    response = api_client.get(
        "/api/v1/knowledge/documents",
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    assert response.status_code == 200
    titles = [d["title"] for d in response.json()["data"]]
    assert "userdoc.pdf" not in titles


def test_upload_preserves_user_id_and_returns_correct_owner(
    api_client, seed_ids, auth_headers
) -> None:
    response = api_client.post(
        "/api/v1/documents/upload",
        files={"file": ("owned.pdf", io.BytesIO(_VALID_PDF), "application/pdf")},
        headers=auth_headers(seed_ids["owner_user_id"]),
    )
    doc = response.json()["data"]["document"]
    assert doc["user_id"] == str(seed_ids["owner_user_id"])
