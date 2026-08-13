"""Conversation memory manager (AI_ARCHITECTURE.md §21, §22.5, §23.1).

Purpose:
    Memory is an explicit component of the AI service, not incidental prompt
    stuffing (§1.4.7). The AI service is stateless — any instance can serve any
    conversation (§1.6) — so this manager is a stateless service: it derives
    session state from persisted data at session start and never holds a
    conversation in-process across runs (§21.4, §22.5).

    It implements the §21 memory model:

    - **Short-term memory** (§21.2): the recent ``CHAT_HISTORY_LIMIT`` turns
      (default 20, §21.6) injected into context. Oldest turns beyond the window
      are summarized rather than dropped wholesale when long-term memory is
      enabled.
    - **Long-term memory** (§21.3): opt-in conversation summaries generated at
      milestones and stored as derived records; on restore the summary plus the
      recent window reconstructs context (§22.5). Summarization is delegated to
      an injected ``summarizer`` callable (LLM-backed in production, a
      deterministic fake in tests) so this module stays offline and provider-
      agnostic.
    - **Session memory** (§21.4): rebuilt from persisted history at session
      start — never held only in-process.
    - **Memory persistence failure** (§23.1): a write failure never fails the
      run; ``persist`` reports the outcome so the caller can retry through
      background handling.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from pydantic import BaseModel, Field

from ai.core.state import ChatTurn, MessageRole


class SessionMemory(BaseModel):
    """Reconstructed session memory for a conversation (§21, §22.5).

    ``history`` is the short-term window (recent ``chat_history_limit`` turns)
    ready to be injected into context; ``summary`` is the optional long-term
    summary reconstructed across sessions (§21.3, §22.5).
    """

    history: list[ChatTurn] = Field(default_factory=list)
    summary: str | None = None


class ConversationMemoryManager:
    """Stateless short/long-term memory service (§21).

    Pure by design: every method takes the current history as an argument and
    returns a derived value, so concurrent runs and multiple instances never
    share mutable memory state (§1.6, §21.4).
    """

    def __init__(
        self,
        *,
        chat_history_limit: int = 20,
        long_term_enabled: bool = False,
        summarizer: Callable[[Sequence[ChatTurn]], str] | None = None,
    ) -> None:
        if chat_history_limit <= 0:
            raise ValueError("chat_history_limit must be a positive integer")
        self.chat_history_limit = chat_history_limit
        self.long_term_enabled = long_term_enabled
        self._summarizer = summarizer

    # --- short-term window (§21.2, §21.6) -----------------------------------

    def window(self, history: Sequence[ChatTurn]) -> list[ChatTurn]:
        """Return the recent ``chat_history_limit`` turns (§21.2).

        The window holds the newest turns that stay in context; anything older
        is handled by ``commit`` (summarized when long-term memory is enabled,
        dropped otherwise, §21.2).
        """
        return list(history[-self.chat_history_limit :]) if history else []

    def add_turn(
        self,
        history: Sequence[ChatTurn],
        *,
        role: MessageRole,
        content: str,
    ) -> tuple[list[ChatTurn], list[ChatTurn]]:
        """Append a turn and enforce the window (§21.2, §21.6).

        Returns ``(updated_window, overflow)`` where ``overflow`` is the oldest
        turns pushed beyond the window. When long-term memory is enabled the
        caller can fold ``overflow`` into the summary; otherwise it is dropped.
        """
        updated = [*history, ChatTurn(role=role, content=content)]
        if len(updated) <= self.chat_history_limit:
            return updated, []
        overflow = updated[: -self.chat_history_limit]
        return updated[-self.chat_history_limit :], overflow

    def commit(
        self,
        history: Sequence[ChatTurn],
        *,
        role: MessageRole,
        content: str,
        current_summary: str | None = None,
    ) -> SessionMemory:
        """Append a turn and return the updated session memory (§21).

        The window is enforced and — when long-term memory is enabled and a
        summarizer is configured — overflow turns are summarized and folded
        into ``current_summary`` rather than dropped wholesale (§21.2-21.3).
        """
        window, overflow = self.add_turn(history, role=role, content=content)
        summary = current_summary
        if overflow and self.long_term_enabled and self._summarizer is not None:
            overflow_text = self._summarizer(overflow)
            if overflow_text.strip():
                summary = _merge_summaries(current_summary, overflow_text)
        return SessionMemory(history=window, summary=summary)

    # --- session memory (§21.4, §22.5) --------------------------------------

    def rebuild(
        self,
        persisted: Sequence[ChatTurn],
        summary: str | None = None,
    ) -> SessionMemory:
        """Reconstruct session memory from persisted data (§21.4, §22.5).

        The short-term window is derived from the persisted ``chat_history``
        rows and the optional long-term summary is carried over so a restored
        conversation keeps full context.
        """
        return SessionMemory(history=self.window(persisted), summary=summary)

    # --- persistence (§23.1) ------------------------------------------------

    def persist(
        self,
        history: Sequence[ChatTurn],
        writer: Callable[[Sequence[ChatTurn]], object],
    ) -> bool:
        """Persist the history through ``writer`` without failing the run.

        A DB write failure (the §23.1 memory persistence failure) returns
        ``False`` so the caller can retry through background handling; it never
        raises, because the run must still complete and return to the caller.
        """
        try:
            writer(history)
        except Exception:
            return False
        return True


def _merge_summaries(existing: str | None, addition: str) -> str:
    """Combine prior long-term summaries with a new one (§21.3)."""
    if existing:
        return f"{existing}\n{addition}"
    return addition
