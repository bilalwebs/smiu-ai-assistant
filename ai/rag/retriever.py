"""Retriever contract (AI_ARCHITECTURE.md §16).

Purpose:
    The retrieval interface every specialist agent consumes. Phase 9 implements
    the concrete FAISS-backed retriever against this protocol; Phase 8 agents
    depend only on the protocol so retrieval can be faked in offline suites and
    swapped at configuration time (AI_ARCHITECTURE.md §14-16, §16.5).

Contract rules (AI_ARCHITECTURE.md §16.4-16.5):
    - ``categories`` narrows the search to the specialist's knowledge scope
      (admission / examination / faq / documents),
    - only ``processed`` + ``is_active`` current-version documents are
      candidates — the concrete implementation enforces this,
    - ``top_k`` bounds the returned chunks; chunks always carry source metadata
      so the context builder and the citation assembler can use it (§19.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ai.core.state import RetrievedChunk


@runtime_checkable
class Retriever(Protocol):
    """Retrieval interface consumed by specialist agents (§16).

    ``RetrievedChunk.score`` is the raw similarity score from the index (§16.3);
    it is not normalized. A retriever returns the top ``top_k`` chunks in
    descending score order, already filtered by document status/version and
    scoped to the requested categories.
    """

    def retrieve(
        self,
        *,
        query: str,
        categories: Sequence[str] = (),
        top_k: int = 4,
    ) -> list[RetrievedChunk]:
        """Return the best-matching knowledge chunks for ``query`` (§16)."""
        ...
