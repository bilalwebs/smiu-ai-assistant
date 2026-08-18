"""Document schemas (API_SPECIFICATION.md).

Purpose:
    Define the request/response payloads for document upload and retrieval.
    The ``DocumentRead`` schema is the primary response for upload and
    listing endpoints; ``DocumentUploadResponse`` wraps it with upload-specific
    metadata.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.base import ApiModel, UtcDateTime


class DocumentRead(ApiModel):
    """Document metadata returned to the client."""

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    category: str
    original_filename: str
    content_type: str | None = None
    size_bytes: int
    status: str
    created_at: UtcDateTime
    updated_at: UtcDateTime


class DocumentUploadResponse(BaseModel):
    """Response envelope for a successful file upload."""

    document: DocumentRead
    message: str = "File uploaded successfully"


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentRead]
    total: int
