"""Context Builder unit tests (Phase 9 RAG task 5, AI_ARCHITECTURE.md §17).

Scope:
    - assembly order and labeled blocks (§17.2): system rules → user context →
      history → retrieved evidence → current query,
    - deterministic token estimation (§17.3) using the codebase's
      ``max(1, len(text) // 4)`` approximation — never a tokenizer download,
    - token budgeting/trimming (§17.3-17.4): evidence lowest-score first, then
      history oldest-first, then user context; system rules + current query are
      never trimmed,
    - ``ContextOverflowError`` only when the essential content cannot fit —
      never a silent truncation and never an unbounded budget overshoot,
    - empty retrieval, exact budget boundary, oversized individual chunks,
      chunk metadata / chunk-identity preservation, and no fabricated content.

Budget accounting: the builder sizes each trimmable *unit* (source block,
history turn, user-context section) against the budget; the small render
headers ([Conversation history], [Retrieved evidence ...]) sit inside the
safety margin reserved by §17.3 ("per-model context window minus a reserved
safety margin"), so this suite asserts the accounted invariant and a bounded
render overhead. All tests are deterministic and fully offline — synthetic
``RetrievedChunk`` objects and an injectable character-count estimator.
"""

from __future__ import annotations

import uuid

import pytest

from ai.core.state import ChatTurn, MessageRole, RetrievedChunk, UserContext, UserRole
from ai.rag.context_builder import ContextBuilder, ContextOverflowError

# Largest possible render overhead: the two group headers plus the block
# separators added at render time beyond the accounted unit texts (§17.3
# safety margin absorbs these).
_MAX_RENDER_OVERHEAD = 100


def _chunk(
    chunk_id: str,
    *,
    score: float = 0.8,
    title: str = "Admission Policy",
    snippet: str = "Applicants need 60% in intermediate to be eligible.",
    category: str = "admission",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        title=title,
        category=category,
        snippet=snippet,
        score=score,
    )


def _user() -> UserContext:
    return UserContext(user_id=uuid.uuid4(), user_role=UserRole.STUDENT, department="CS")


def _history(*contents: str) -> list[ChatTurn]:
    return [ChatTurn(role=MessageRole.USER, content=content) for content in contents]


def _char(text: str) -> int:
    """Character-count estimator for exact, predictable budgeting in tests."""
    return len(text)


def _builder(max_tokens: int) -> ContextBuilder:
    return ContextBuilder(max_tokens=max_tokens, estimate_tokens=_char)


# Exact accounted size of each unit — mirrors the builder's block formats so
# budgets land in the precise range that exercises a specific trim.
def _source_len(chunk: RetrievedChunk, index: int) -> int:
    return len(
        f"[Source {index}] {chunk.title} (category: {chunk.category}) "
        f"[chunk: {chunk.chunk_id}]\n{chunk.snippet}"
    )


def _query_len(query: str) -> int:
    return len(f"[Current question]\n{query}")


def _history_len(content: str) -> int:
    return len(f"- user: {content}")


def _rules_len(rules: str) -> int:
    return len(rules)


def _user_section_len(user_context: UserContext) -> int:
    return len(
        "[User context]\n"
        f"role: {user_context.user_role.value}\n"
        f"department: {user_context.department or 'unknown'}\n"
        f"locale: {user_context.locale}"
    )


def _full_context(
    *,
    query: str,
    evidence: list[RetrievedChunk] | None = None,
    history: list[ChatTurn] | None = None,
    user_context: UserContext | None = None,
    system_rules: str = "",
) -> str:
    """Build with an effectively unlimited budget (every unit survives)."""
    builder = ContextBuilder(max_tokens=10_000_000, estimate_tokens=_char)
    return builder.build(
        query=query,
        evidence=evidence or [],
        message_history=history or [],
        user_context=user_context,
        system_rules=system_rules,
    )


# --- Assembly order and labeling (§17.2) -------------------------------------


def test_empty_retrieval_renders_just_the_question() -> None:
    context = _full_context(query="What is the deadline?")
    assert context == "[Current question]\nWhat is the deadline?"
    assert "[Retrieved evidence" not in context
    assert "[Conversation history]" not in context
    assert "[User context]" not in context


def test_sections_are_ordered_and_labeled() -> None:
    context = _full_context(
        query="What is the deadline?",
        evidence=[_chunk("c1")],
        history=_history("About admission"),
        user_context=_user(),
        system_rules="SYSTEM RULES",
    )
    assert context.index("SYSTEM RULES") < context.index("[User context]")
    assert context.index("[User context]") < context.index("[Conversation history]")
    assert context.index("[Conversation history]") < context.index("[Retrieved evidence")
    assert context.index("[Retrieved evidence") < context.index("[Current question]")


def test_evidence_is_separated_from_instruction() -> None:
    context = _full_context(query="deadline?", evidence=[_chunk("c1")])
    assert "[Retrieved evidence — answer only from this evidence]" in context
    assert "[Current question]" in context
    assert context.index("[Retrieved evidence") < context.index("[Current question]")


# --- Budgeting, boundary, and trimming (§17.3-17.4) --------------------------


def test_single_chunk_within_budget_is_rendered() -> None:
    builder = _builder(max_tokens=10_000)
    context = builder.build(query="deadline?", evidence=[_chunk("c1")])
    assert "[Source 1] Admission Policy (category: admission)" in context
    assert "Applicants need 60% in intermediate to be eligible." in context
    assert "[Current question]" in context


def test_multiple_chunks_within_budget_preserve_order() -> None:
    chunks = [
        _chunk("c1", score=0.9, snippet="first snippet"),
        _chunk("c2", score=0.7, snippet="second snippet"),
        _chunk("c3", score=0.5, snippet="third snippet"),
    ]
    context = _full_context(query="q", evidence=chunks)
    assert context.index("first snippet") < context.index("second snippet")
    assert context.index("second snippet") < context.index("third snippet")


def test_exact_budget_boundary_keeps_everything() -> None:
    chunks = [_chunk("c1", snippet="snippet one"), _chunk("c2", snippet="snippet two")]
    history = _history("recent turn")
    accounted = (
        _source_len(chunks[0], 1)
        + _source_len(chunks[1], 2)
        + _history_len("recent turn")
        + _user_section_len(_user())
        + _query_len("q")
    )
    full = _full_context(query="q", evidence=chunks, history=history, user_context=_user())
    builder = _builder(max_tokens=accounted)
    context = builder.build(
        query="q",
        evidence=chunks,
        message_history=history,
        user_context=_user(),
    )
    assert context == full
    assert builder.estimate_tokens(context) <= accounted + _MAX_RENDER_OVERHEAD


def test_over_budget_trims_lowest_score_evidence_first() -> None:
    high = _chunk("high", score=0.9, snippet="high-scoring merit content")
    low = _chunk("low", score=0.1, snippet="low-scoring stale content")
    accounted = _source_len(high, 1) + _source_len(low, 2) + _query_len("deadline?")
    builder = _builder(max_tokens=accounted - 1)
    context = builder.build(query="deadline?", evidence=[high, low])
    assert "high-scoring merit content" in context
    assert "low-scoring stale content" not in context
    assert "[Current question]" in context
    assert builder.estimate_tokens(context) <= accounted - 1 + _MAX_RENDER_OVERHEAD


def test_chunks_that_fit_individually_but_exceed_total_are_trimmed() -> None:
    a = _chunk("a", score=0.8, snippet="chunk a fits alone")
    b = _chunk("b", score=0.6, snippet="chunk b fits alone")
    alone = _source_len(a, 1) + _query_len("q")
    both = _source_len(a, 1) + _source_len(b, 2) + _query_len("q")
    budget = both - 1
    assert alone <= budget < both  # a fits alone; a + b does not
    builder = _builder(max_tokens=budget)
    context = builder.build(query="q", evidence=[a, b])
    assert "chunk a fits alone" in context
    assert "chunk b fits alone" not in context
    assert builder.estimate_tokens(context) <= budget + _MAX_RENDER_OVERHEAD


def test_oversized_individual_chunk_is_dropped_safely() -> None:
    huge = _chunk("huge", snippet="x" * 500)
    accounted = _source_len(huge, 1) + _query_len("q")
    builder = _builder(max_tokens=accounted - 1)
    context = builder.build(query="q", evidence=[huge])
    assert "x" * 500 not in context
    assert context == "[Current question]\nq"
    assert builder.estimate_tokens(context) <= accounted - 1 + _MAX_RENDER_OVERHEAD


def test_system_rules_never_trimmed_before_other_content() -> None:
    rules = "SYSTEM RULES"
    history = _history("older turn that is long enough", "recent turn")
    budget = (
        _rules_len(rules)
        + _query_len("q")
        + 1  # room only for rules + query — all history must go
    )
    builder = _builder(max_tokens=budget)
    context = builder.build(query="q", message_history=history, system_rules=rules)
    assert "SYSTEM RULES" in context
    assert "[Current question]" in context
    assert "recent turn" not in context
    assert "older turn that is long enough" not in context
    assert builder.estimate_tokens(context) <= budget + _MAX_RENDER_OVERHEAD


def test_history_trimmed_oldest_first() -> None:
    history = _history("oldest turn that is long enough", "recent turn")
    accounted = (
        _history_len("oldest turn that is long enough")
        + _history_len("recent turn")
        + _query_len("next?")
    )
    builder = _builder(max_tokens=accounted - 1)
    context = builder.build(query="next?", message_history=history)
    assert "recent turn" in context
    assert "oldest turn that is long enough" not in context
    assert "[Current question]" in context


def test_user_context_dropped_before_evidence() -> None:
    evidence = [_chunk("keep", snippet="keep this evidence block")]
    accounted = _user_section_len(_user()) + _source_len(evidence[0], 1) + _query_len("q")
    builder = _builder(max_tokens=accounted - 1)
    context = builder.build(query="q", evidence=evidence, user_context=_user())
    assert "keep this evidence block" in context
    assert "[User context]" not in context
    assert builder.estimate_tokens(context) <= accounted - 1 + _MAX_RENDER_OVERHEAD


def test_budget_overshoot_is_bounded_not_silently_unbounded() -> None:
    chunks = [_chunk(f"c{i}", score=0.9 - i * 0.1) for i in range(4)]
    history = _history("one", "two", "three")
    for budget in (200, 150, 100, 60, 40):
        builder = _builder(max_tokens=budget)
        context = builder.build(
            query="q",
            evidence=chunks,
            message_history=history,
            user_context=_user(),
        )
        assert "[Current question]" in context
        assert builder.estimate_tokens(context) <= budget + _MAX_RENDER_OVERHEAD


# --- Determinism and token estimation (§17.3) --------------------------------


def test_deterministic_output_for_identical_inputs() -> None:
    chunks = [_chunk("c1"), _chunk("c2")]
    history = _history("recent")
    first = _full_context(query="q", evidence=chunks, history=history, user_context=_user())
    second = _full_context(query="q", evidence=chunks, history=history, user_context=_user())
    assert first == second
    builder = _builder(max_tokens=100)
    a = builder.build(query="q", evidence=chunks, message_history=history)
    b = builder.build(query="q", evidence=chunks, message_history=history)
    assert a == b


def test_default_estimator_matches_len_divided_by_four() -> None:
    builder = ContextBuilder(max_tokens=10_000)
    assert builder.estimate_tokens("") == 1
    assert builder.estimate_tokens("abcd") == 1
    assert builder.estimate_tokens("a" * 16) == 4
    assert builder.estimate_tokens("a" * 399) == 99
    assert builder.estimate_tokens("a" * 400) == 100


def test_estimator_is_injectable() -> None:
    builder = ContextBuilder(max_tokens=10_000, estimate_tokens=_char)
    assert builder.estimate_tokens("hello") == 5


# --- Metadata / chunk identity preservation (§17.2, §19.1) -------------------


def test_metadata_and_chunk_identity_are_preserved() -> None:
    chunks = [
        _chunk("ad-123", title="Merit Policy", category="admission", snippet="60% required."),
        _chunk("ex-456", title="Exam Schedule", category="examination", snippet="Results in June."),
    ]
    context = _full_context(query="q", evidence=chunks)
    assert "ad-123" in context
    assert "ex-456" in context
    assert "Merit Policy" in context
    assert "category: admission" in context
    assert "category: examination" in context
    assert context.index("ad-123") < context.index("ex-456")


def test_chunk_identity_is_never_fabricated() -> None:
    context = _full_context(query="q", evidence=[_chunk("real-id", snippet="real content")])
    assert "real-id" in context
    assert "ghost-id" not in context


def test_no_fabricated_content() -> None:
    marker = "zz-unrelated-marker-zz"
    context = _full_context(
        query="q",
        evidence=[_chunk("c1", snippet="provided snippet")],
        history=_history("provided history"),
        user_context=_user(),
        system_rules="provided rules",
    )
    assert marker not in context
    assert "provided snippet" in context
    assert "provided history" in context
    assert "provided rules" in context


def test_malformed_chunk_still_renders_without_crashing() -> None:
    chunk = RetrievedChunk(
        chunk_id="edge",
        title="",
        category="",
        snippet="still real content",
        score=0.0,
    )
    context = _full_context(query="q", evidence=[chunk])
    assert "still real content" in context
    assert "[chunk: edge]" in context


# --- ContextOverflowError (§17.3) --------------------------------------------


def test_overflow_raised_only_when_essential_content_exceeds_budget() -> None:
    builder = _builder(max_tokens=10)
    with pytest.raises(ContextOverflowError):
        builder.build(
            query="a question that is much longer than ten characters",
            system_rules="system rules that also exceed the budget",
        )


def test_overflow_not_raised_when_only_removable_content_exceeds() -> None:
    builder = _builder(max_tokens=_query_len("q"))
    context = builder.build(
        query="q",
        evidence=[_chunk("huge", snippet="x" * 500)],
        message_history=_history("y" * 500),
    )
    assert context == "[Current question]\nq"
