"""``knowledge_chunks`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §21.2).

AI & Knowledge: retrievable units plus FAISS mapping. Chunks are derived units
of a document — no soft delete; the service maintains the parent document's
``chunk_count`` and enforces unique chunk ordering (DATABASE_DESIGN.md §21.2).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk
from app.repositories import KnowledgeChunkRepository, KnowledgeDocumentRepository
from app.services.base import BaseService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


class KnowledgeChunkService(BaseService):
    """Knowledge chunk operations for :class:`app.models.knowledge_chunks.KnowledgeChunk`."""

    def __init__(
        self,
        session: AsyncSession,
        chunks: KnowledgeChunkRepository | None = None,
        documents: KnowledgeDocumentRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._chunks = chunks or KnowledgeChunkRepository(session)
        self._documents = documents or KnowledgeDocumentRepository(session)

    async def create_chunk(
        self,
        *,
        knowledge_document_id: uuid.UUID,
        chunk_index: int,
        chunk_text: str,
        vector_id: str | None = None,
        heading: str | None = None,
        page_number: int | None = None,
        token_count: int | None = None,
        character_count: int | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> KnowledgeChunk:
        """Create a chunk and bump its parent document's chunk count."""
        document = await self._documents.get_by_id(knowledge_document_id)
        if document is None:
            raise NotFoundError(message="Knowledge document not found")
        self._validate_counts(
            chunk_index=chunk_index,
            page_number=page_number,
            token_count=token_count,
            character_count=character_count,
        )
        chunk_text = self._validate_not_blank(chunk_text, field="chunk_text")
        existing = await self._chunks.get(
            KnowledgeChunk.knowledge_document_id == knowledge_document_id,
            KnowledgeChunk.chunk_index == chunk_index,
        )
        if existing is not None:
            raise ConflictError(
                message="A chunk with this index already exists in the document",
                details=[{"field": "chunk_index", "reason": "already in use"}],
            )
        values: dict[str, Any] = {
            "knowledge_document_id": knowledge_document_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "vector_id": vector_id,
            "heading": heading,
            "page_number": page_number,
            "token_count": token_count,
            "character_count": character_count,
        }
        if metadata_ is not None:
            values["metadata_"] = metadata_
        chunk = await self._chunks.create(**values)
        await self._documents.update(
            document, chunk_count=document.chunk_count + 1
        )
        return chunk

    async def update_chunk(
        self, *, chunk_id: uuid.UUID, **changes: Any
    ) -> KnowledgeChunk:
        """Update chunk content/position with per-field validation."""
        chunk = await self._require_chunk(chunk_id)
        if "chunk_text" in changes:
            changes["chunk_text"] = self._validate_not_blank(
                changes["chunk_text"], field="chunk_text"
            )
        self._validate_counts(
            chunk_index=changes.get("chunk_index", chunk.chunk_index),
            page_number=changes.get("page_number", chunk.page_number),
            token_count=changes.get("token_count", chunk.token_count),
            character_count=changes.get("character_count", chunk.character_count),
        )
        if "chunk_index" in changes and changes["chunk_index"] != chunk.chunk_index:
            existing = await self._chunks.get(
                KnowledgeChunk.knowledge_document_id == chunk.knowledge_document_id,
                KnowledgeChunk.chunk_index == changes["chunk_index"],
            )
            if existing is not None and existing.id != chunk.id:
                raise ConflictError(
                    message="A chunk with this index already exists in the document",
                    details=[{"field": "chunk_index", "reason": "already in use"}],
                )
        return await self._chunks.update(chunk, **changes)

    async def list_chunks(
        self, *, knowledge_document_id: uuid.UUID
    ) -> list[KnowledgeChunk]:
        """List a document's chunks in index order."""
        if await self._documents.get_by_id(knowledge_document_id) is None:
            raise NotFoundError(message="Knowledge document not found")
        return await self._chunks.list_by_document(knowledge_document_id)

    @staticmethod
    def _validate_counts(
        *,
        chunk_index: int,
        page_number: int | None,
        token_count: int | None,
        character_count: int | None,
    ) -> None:
        """Enforce non-negative/positive ranges on the numeric chunk fields."""
        if chunk_index < 0:
            raise ValidationError(
                message="chunk_index must not be negative",
                details=[{"field": "chunk_index", "reason": "negative"}],
            )
        if page_number is not None and page_number < 1:
            raise ValidationError(
                message="page_number must be positive",
                details=[{"field": "page_number", "reason": "must be positive"}],
            )
        if token_count is not None and token_count < 0:
            raise ValidationError(
                message="token_count must not be negative",
                details=[{"field": "token_count", "reason": "negative"}],
            )
        if character_count is not None and character_count < 0:
            raise ValidationError(
                message="character_count must not be negative",
                details=[{"field": "character_count", "reason": "negative"}],
            )

    async def _require_chunk(self, chunk_id: uuid.UUID) -> KnowledgeChunk:
        chunk = await self._chunks.get_by_id(chunk_id)
        if chunk is None:
            raise NotFoundError(message="Knowledge chunk not found")
        return chunk
