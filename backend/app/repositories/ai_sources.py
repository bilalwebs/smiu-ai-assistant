"""``ai_sources`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §22).

AI & Knowledge: citations attached to assistant messages, powering the
"always cite RAG sources" rule and the collapsible Sources UI.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import AISource
from app.repositories.base import BaseRepository


class AISourceRepository(BaseRepository[AISource]):
    """Data access for :class:`app.models.ai_sources.AISource`."""

    model = AISource

    async def list_by_message(
        self,
        message_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[AISource]:
        """List citations for an assistant message in retrieval order."""
        return await self.list(
            AISource.message_id == message_id,
            order_by=[AISource.retrieved_at.asc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["AISourceRepository"]
