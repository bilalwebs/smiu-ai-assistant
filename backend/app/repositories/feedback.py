"""``feedback`` repository (BACKEND_ARCHITECTURE.md §12; DATABASE_DESIGN.md §23).

Workflow & Support: user ratings, comments, and flags on AI messages,
supporting the thumbs-up/down UI and model quality evaluation.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.sql.base import ExecutableOption

from app.models import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    """Data access for :class:`app.models.feedback.Feedback`."""

    model = Feedback

    async def list_by_message(
        self,
        message_id: uuid.UUID,
        *,
        options: Sequence[ExecutableOption] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Feedback]:
        """List feedback on an AI message, newest first."""
        return await self.list(
            Feedback.message_id == message_id,
            order_by=[Feedback.created_at.desc()],
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
    ) -> list[Feedback]:
        """List a user's feedback, newest first."""
        return await self.list(
            Feedback.user_id == user_id,
            order_by=[Feedback.created_at.desc()],
            options=options,
            limit=limit,
            offset=offset,
        )


__all__ = ["FeedbackRepository"]
