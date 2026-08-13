"""Context builder (AI_ARCHITECTURE.md §17).

Purpose:
    Assembles the LLM context within a token budget: user context, the
    short-term memory window, retrieved evidence, and the current query — in a
    defined order with labeled blocks so the LLM can attribute each part (§17.2).
    The builder is the RAG pipeline's context-injection template (§13.2).

Assembly order (§17.2):
    system rules → user context → history window → retrieved evidence → query

Prioritization when over budget (§17.3-17.4):
    system rules and the current query are never trimmed;
    evidence chunks drop lowest-score-first, then history turns oldest-first,
    then the user-context section. Content is never silently truncated
    (AI_ARCHITECTURE.md §21.6); if even the essential content exceeds the
    budget a ``ContextOverflowError`` is raised.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ai.core.state import ChatTurn, RetrievedChunk, UserContext

TokenEstimator = Callable[[str], int]

# Keep priority per §17.4 (higher = survives trimming first).
_PRIORITY_NEVER_TRIM = 10
_PRIORITY_EVIDENCE = 9
_PRIORITY_HISTORY = 5
_PRIORITY_USER_CONTEXT = 1


class ContextOverflowError(Exception):
    """The context cannot fit in the budget even after trimming (§17.3).

    Raised only when the essential content (system rules + current query)
    exceeds the budget — a configuration error, never a silent truncation.
    """


@dataclass(frozen=True)
class _Unit:
    """One trimmable context unit (a section, a history turn, a source block).

    ``order`` is the unit's position in the assembled prompt; among units of
    equal keep-priority the later unit is trimmed first (oldest history turn,
    lowest-score evidence chunk).
    """

    text: str
    priority: int
    order: int
    kind: str  # "rules" | "user_context" | "history" | "evidence" | "query"


class ContextBuilder:
    """Budgeted, labeled context assembly for grounded generation (§17)."""

    def __init__(
        self,
        *,
        max_tokens: int,
        estimate_tokens: TokenEstimator | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self._estimate_tokens = estimate_tokens or _default_estimator

    def build(
        self,
        *,
        query: str,
        evidence: Sequence[RetrievedChunk] = (),
        message_history: Sequence[ChatTurn] = (),
        user_context: UserContext | None = None,
        system_rules: str = "",
    ) -> str:
        """Return the budgeted, labeled prompt context (§17.2)."""
        units: list[_Unit] = []

        if system_rules:
            units.append(_Unit(system_rules, _PRIORITY_NEVER_TRIM, len(units), "rules"))

        if user_context is not None:
            units.append(
                _Unit(
                    self._user_context_section(user_context),
                    _PRIORITY_USER_CONTEXT,
                    len(units),
                    "user_context",
                )
            )

        # Recent turns first so continuity is immediately visible (§17.4).
        for turn in reversed(message_history):
            units.append(
                _Unit(
                    f"- {turn.role.value}: {turn.content}",
                    _PRIORITY_HISTORY,
                    len(units),
                    "history",
                )
            )

        # Evidence arrives score-descending (§16.5); the lowest-score chunk is
        # trimmed first when over budget (§17.4).
        for index, chunk in enumerate(evidence, start=1):
            units.append(
                _Unit(
                    self._source_block(chunk, index),
                    _PRIORITY_EVIDENCE,
                    len(units),
                    "evidence",
                )
            )

        units.append(
            _Unit(
                f"[Current question]\n{query}",
                _PRIORITY_NEVER_TRIM,
                len(units),
                "query",
            )
        )

        kept = self._fit(units)
        return self._render(kept)

    def _fit(self, units: list[_Unit]) -> list[_Unit]:
        """Drop lowest-priority units until the context fits the budget."""
        budget = self.max_tokens
        total = sum(self._estimate_tokens(unit.text) for unit in units)
        if total <= budget:
            return units

        removable = sorted(
            (unit for unit in units if unit.priority < _PRIORITY_NEVER_TRIM),
            key=lambda unit: (unit.priority, -unit.order),
        )
        remaining = {unit.order: unit for unit in units}
        over = total - budget
        for unit in removable:
            remaining.pop(unit.order)
            over -= self._estimate_tokens(unit.text)
            if over <= 0:
                break

        kept = [unit for order, unit in sorted(remaining.items())]
        essential = sum(self._estimate_tokens(unit.text) for unit in kept)
        if essential > budget:
            raise ContextOverflowError(
                "context cannot fit within the budget after trimming "
                "(system rules + current query exceed the context budget)"
            )
        return kept

    def _render(self, kept: list[_Unit]) -> str:
        """Assemble surviving units in canonical order with group headers."""
        rules = [unit.text for unit in kept if unit.kind == "rules"]
        user_context = [unit.text for unit in kept if unit.kind == "user_context"]
        history = [unit.text for unit in kept if unit.kind == "history"]
        evidence = [unit.text for unit in kept if unit.kind == "evidence"]
        query = [unit.text for unit in kept if unit.kind == "query"]

        blocks: list[str] = []
        blocks.extend(rules)
        blocks.extend(user_context)
        if history:
            blocks.append("[Conversation history]\n" + "\n".join(history))
        if evidence:
            blocks.append(
                "[Retrieved evidence — answer only from this evidence]\n"
                + "\n\n".join(evidence)
            )
        blocks.extend(query)
        return "\n\n".join(blocks)

    def _user_context_section(self, user_context: UserContext) -> str:
        return (
            "[User context]\n"
            f"role: {user_context.user_role.value}\n"
            f"department: {user_context.department or 'unknown'}\n"
            f"locale: {user_context.locale}"
        )

    def _source_block(self, chunk: RetrievedChunk, index: int) -> str:
        return (
            f"[Source {index}] {chunk.title} (category: {chunk.category})\n"
            f"{chunk.snippet}"
        )


def _default_estimator(text: str) -> int:
    """Approximate English tokens-per-character ratio (≈4 chars/token)."""
    return max(1, len(text) // 4)
