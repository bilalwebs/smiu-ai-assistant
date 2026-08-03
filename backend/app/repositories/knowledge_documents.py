"""``knowledge_documents`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §21.1).

AI & Knowledge: source metadata for indexed RAG documents — category search and
the active-document set used by retrieval.
"""

from __future__ import annotations

from app.models import KnowledgeCategory, KnowledgeDocument
from app.repositories.base import BaseRepository


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    """Data access for :class:`app.models.knowledge_documents.KnowledgeDocument`."""

    model = KnowledgeDocument

    async def search_by_category(
        self,
        category: KnowledgeCategory,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[KnowledgeDocument]:
        """List live, active documents in a category, alphabetically."""
        return await self.list(
            KnowledgeDocument.category == category,
            KnowledgeDocument.is_active.is_(True),
            order_by=[KnowledgeDocument.title.asc()],
            limit=limit,
            offset=offset,
        )

    async def get_active_documents(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[KnowledgeDocument]:
        """List live, active documents, newest first."""
        return await self.list(
            KnowledgeDocument.is_active.is_(True),
            order_by=[KnowledgeDocument.created_at.desc()],
            limit=limit,
            offset=offset,
        )


__all__ = ["KnowledgeDocumentRepository"]
