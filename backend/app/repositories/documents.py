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
        conversation_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Document]:
        """List documents linked to a conversation via chat messages.

        Joins through ``chat_history`` on ``Document.message_id`` to filter
        documents whose linked message belongs to the given conversation.
        """
        from sqlalchemy import select
        from app.models import ChatMessage

        stmt = (
            select(Document)
            .join(ChatMessage, Document.message_id == ChatMessage.id)
            .where(
                ChatMessage.conversation_id == conversation_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


__all__ = ["DocumentRepository"]
