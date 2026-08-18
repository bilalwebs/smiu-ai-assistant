"""``documents`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §20).

Workflow & Support: metadata for uploaded files. Only metadata is persisted;
file bytes live on the dedicated storage path.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Data access for :class:`app.models.documents.Document`."""

    model = Document

    async def list_by_request(
        self,
        request_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Document]:
        """List a request's attachments in upload order."""
        return await self.list(
            Document.request_id == request_id,
            order_by=[Document.created_at.asc()],
            options=options,
            limit=limit,
            offset=offset,
        )

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Document]:
        """List a user's documents, newest first."""
        return await self.list(
            Document.user_id == user_id,
            order_by=[Document.created_at.desc()],
            options=options,
            limit=limit,
            offset=offset,
        )

    async def list_by_conversation(
        self,
        user_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Document]:
        """List a user's documents linked via their chat messages in any conversation.

        Documents are associated with users directly (user_id). This lists all
        documents owned by a user, scoped to their user_id.
        """
        return await self.list(
            Document.user_id == user_id,
            order_by=[Document.created_at.desc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["DocumentRepository"]
