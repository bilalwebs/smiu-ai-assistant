"""``knowledge_chunks`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §21.2).

AI & Knowledge: retrievable units plus FAISS mapping. No soft delete — chunks
die with their document (CASCADE).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import KnowledgeChunk
from app.repositories.base import BaseRepository


class KnowledgeChunkRepository(BaseRepository[KnowledgeChunk]):
    """Data access for :class:`app.models.knowledge_chunks.KnowledgeChunk`."""

    model = KnowledgeChunk

    async def list_by_document(
        self,
        knowledge_document_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[KnowledgeChunk]:
        """List a document's chunks in index order."""
        return await self.list(
            KnowledgeChunk.knowledge_document_id == knowledge_document_id,
            order_by=[KnowledgeChunk.chunk_index.asc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["KnowledgeChunkRepository"]
