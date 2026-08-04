"""Knowledge base schemas (API_SPECIFICATION.md §23).

Purpose:
    Define the read-side knowledge payloads: indexed document metadata and
    their retrievable chunks (DATABASE_DESIGN.md §21.1-21.2).
"""

from __future__ import annotations

import uuid

from app.models import KnowledgeCategory, KnowledgeStatus
from app.schemas.base import ApiModel, UtcDateTime


class KnowledgeDocumentRead(ApiModel):
    """Indexed RAG source document metadata (§21.1)."""

    id: uuid.UUID
    title: str
    category: KnowledgeCategory
    source_path: str
    file_type: str | None = None
    file_size: int | None = None
    author: str | None = None
    version: str
    checksum_sha256: str
    status: KnowledgeStatus
    chunk_count: int
    is_active: bool
    indexed_at: UtcDateTime | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class KnowledgeChunkRead(ApiModel):
    """Retrievable chunk of a knowledge document (§21.2)."""

    id: uuid.UUID
    knowledge_document_id: uuid.UUID
    chunk_index: int
    chunk_text: str
    vector_id: str | None = None
    heading: str | None = None
    page_number: int | None = None
    token_count: int | None = None
    character_count: int | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime
