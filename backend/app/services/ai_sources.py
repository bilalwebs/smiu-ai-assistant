"""``ai_sources`` service (BACKEND_ARCHITECTURE.md §11; DATABASE_DESIGN.md §22).

AI & Knowledge: citations attached to assistant messages — enforcing the
"always cite RAG sources" rule and the one-citation-per-chunk-per-message
dedup from the partial unique index (DATABASE_DESIGN.md §22.2).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AISource, SourceType
from app.repositories import (
    AISourceRepository,
    ChatMessageRepository,
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from app.services.base import BaseService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


class AISourceService(BaseService):
    """Citation operations for :class:`app.models.ai_sources.AISource`."""

    def __init__(
        self,
        session: AsyncSession,
        sources: AISourceRepository | None = None,
        messages: ChatMessageRepository | None = None,
        documents: KnowledgeDocumentRepository | None = None,
        chunks: KnowledgeChunkRepository | None = None,
    ) -> None:
        super().__init__(session)
        self._sources = sources or AISourceRepository(session)
        self._messages = messages or ChatMessageRepository(session)
        self._documents = documents or KnowledgeDocumentRepository(session)
        self._chunks = chunks or KnowledgeChunkRepository(session)

    async def create_source(
        self,
        *,
        message_id: uuid.UUID,
        source_title: str,
        source_type: SourceType = SourceType.RAG,
        knowledge_document_id: uuid.UUID | None = None,
        knowledge_chunk_id: uuid.UUID | None = None,
        source_url: str | None = None,
        category: str | None = None,
        relevance_score: float | None = None,
        snippet: str | None = None,
    ) -> AISource:
        """Attach a citation to an assistant message."""
        if await self._messages.get_by_id(message_id) is None:
            raise NotFoundError(message="Message not found")
        source_title = self._validate_not_blank(source_title, field="source_title")
        source_type = self._validate_enum(source_type, SourceType, field="source_type")
        if (
            relevance_score is not None
            and not 0 <= relevance_score <= 1
        ):
            raise ValidationError(
                message="relevance_score must be between 0 and 1",
                details=[{"field": "relevance_score", "reason": "out of range"}],
            )
        if (
            knowledge_document_id is not None
            and await self._documents.get_by_id(knowledge_document_id) is None
        ):
            raise NotFoundError(message="Knowledge document not found")
        if (
            knowledge_chunk_id is not None
            and await self._chunks.get_by_id(knowledge_chunk_id) is None
        ):
            raise NotFoundError(message="Knowledge chunk not found")
        if knowledge_chunk_id is not None:
            existing = await self._sources.get(
                AISource.message_id == message_id,
                AISource.knowledge_chunk_id == knowledge_chunk_id,
            )
            if existing is not None:
                raise ConflictError(
                    message="This chunk is already cited for this message",
                    details=[{"field": "knowledge_chunk_id", "reason": "already cited"}],
                )
        return await self._sources.create(
            message_id=message_id,
            knowledge_document_id=knowledge_document_id,
            knowledge_chunk_id=knowledge_chunk_id,
            source_type=source_type,
            source_title=source_title,
            source_url=source_url,
            category=category,
            relevance_score=relevance_score,
            snippet=snippet,
        )

    async def update_source(
        self, *, source_id: uuid.UUID, **changes: Any
    ) -> AISource:
        """Update citation snapshot fields with per-field validation."""
        source = await self._require_source(source_id)
        if "source_title" in changes:
            changes["source_title"] = self._validate_not_blank(
                changes["source_title"], field="source_title"
            )
        if "source_type" in changes:
            changes["source_type"] = self._validate_enum(
                changes["source_type"], SourceType, field="source_type"
            )
        if "relevance_score" in changes:
            relevance_score = changes["relevance_score"]
            if relevance_score is not None and not 0 <= relevance_score <= 1:
                raise ValidationError(
                    message="relevance_score must be between 0 and 1",
                    details=[{"field": "relevance_score", "reason": "out of range"}],
                )
        return await self._sources.update(source, **changes)

    async def list_sources(self, *, message_id: uuid.UUID) -> list[AISource]:
        """List citations for a message in retrieval order."""
        if await self._messages.get_by_id(message_id) is None:
            raise NotFoundError(message="Message not found")
        return await self._sources.list_by_message(message_id)

    async def _require_source(self, source_id: uuid.UUID) -> AISource:
        source = await self._sources.get_by_id(source_id)
        if source is None:
            raise NotFoundError(message="AISource not found")
        return source
