"""Backend memory persistence boundary (AI_ARCHITECTURE.md §21, §22.5, §23.1).

Step B of the AI integration boundary: this adapter implements the workflow's
injectable ``persist_writer`` contract
(``Callable[[Sequence[ChatTurn]], object]``) so the §21.2 short-term window the
``persist`` node produces flows through the backend services instead of the
in-memory default (``_noop_persist``). The optional long-term summary (§21.3)
is written best-effort through :meth:`ConversationMemoryWriter.flush` reusing
the existing :class:`~app.services.ai_conversations.ConversationService` —
never a direct model write (BACKEND_ARCHITECTURE.md §20).

Boundary:
    - ``chat_history`` rows stay owned by the facade's
      :class:`~app.services.chat_history.ChatHistoryService` (§20); this writer
      only records windows and the opt-in conversation summary, so no duplicate
      messages or sources are ever created (Step B no-duplicates rule).

Safety (AI_ARCHITECTURE.md §23.1):
    - ``__call__`` is sync — the graph invokes it under ``asyncio.to_thread`` —
      and only records the window in memory, so a write failure never fails the
      run,
    - ``flush`` is best-effort: any failure returns ``False`` and the run result
      is unaffected; it only writes when the stored summary actually changed, so
      an unchanged restore never clobbers a concurrent external update.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.services.ai_conversations import ConversationService

if TYPE_CHECKING:
    from ai.core.state import ChatTurn

logger = logging.getLogger(__name__)


class ConversationMemoryWriter:
    """Backend ``persist_writer``: records windows, flushes the summary.

    Implements ``Callable[[Sequence[ChatTurn]], object]`` — the contract the
    graph's ``persist`` node passes to ``ConversationMemoryManager.persist``
    (AI_ARCHITECTURE.md §21.2, §23.1). Thread-safe: ``__call__`` runs in a
    worker thread under ``asyncio.to_thread`` while ``flush`` runs on the event
    loop.
    """

    def __init__(self, conversations: ConversationService) -> None:
        self._conversations = conversations
        self._lock = threading.Lock()
        self._latest_window: list[Any] = []

    def __call__(self, history: Sequence[ChatTurn]) -> None:
        """Record the post-run short-term window (sync, never raises)."""
        with self._lock:
            self._latest_window = [*history]

    @property
    def latest_window(self) -> list[Any]:
        """Snapshot of the most recent window the workflow persisted."""
        with self._lock:
            return [*self._latest_window]

    async def flush(self, *, conversation_id: uuid.UUID, summary: str) -> bool:
        """Best-effort write of the long-term summary (§21.3, §23.1).

        Only writes when the stored summary differs, so an unchanged restore is
        a no-op and a concurrent external update is never clobbered. Never
        raises: failures return ``False``.
        """
        try:
            conversation = await self._conversations.get_conversation(
                conversation_id=conversation_id
            )
            if conversation.summary == summary:
                return True
            await self._conversations.update_conversation(
                conversation_id=conversation_id,
                summary=summary,
            )
        except Exception:
            logger.exception("Failed to flush conversation memory summary")
            return False
        return True


__all__ = ["ConversationMemoryWriter"]
