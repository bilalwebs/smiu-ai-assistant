"""Shared specialist-agent machinery (AI_ARCHITECTURE.md §3.5, §12.3).

Purpose:
    Every Phase 1 specialist (Admission, Examination, FAQ) is a *stateless
    worker*: it reads task input from graph state, executes, and writes results
    back (§12.3). The pipeline is identical for all of them — retrieve (§16),
    build context within budget (§17), grounded generation (§18), and citation
    assembly (§19) — only the domain prompt, retrieval scope, and fallback
    department differ. This base implements that pipeline once so new agents
    are added by configuration, not new plumbing (§8 registration rules).

Safety properties:
    - no-answer policy: with no evidence, the specialist returns a grounded
      "information unavailable" response and never fabricates (§20.4, §28.3),
    - generation is schema-constrained structured output (§18.2, §35.2);
      malformed provider output degrades to a safe no-answer, never a crash,
    - provider failures degrade to a friendly FALLBACK response with no
      fabricated content and no secret leakage (§23.1-23.2),
    - guardrails (§25-26): input safety runs before generation (blocked input
      short-circuits with a safe fallback, never reaching the LLM); output
      safety runs after generation and before delivery (blocked output is
      replaced with a safe fallback, §26.4). Internal detection details are
      never surfaced to users.
"""

from __future__ import annotations

import json
import math
from abc import ABC
from collections.abc import Sequence

from pydantic import BaseModel, Field

from ai.core.state import (
    AgentKey,
    AgentOutput,
    ChatTurn,
    Citation,
    RetrievedChunk,
    UserContext,
    WorkflowStatus,
)
from ai.gateway.base import LLMError, LLMGateway
from ai.guardrails.guardrails import GuardrailCategory, SafetyGuardrails, default_guardrails
from ai.prompts.repository import Prompt, PromptRepository, default_repository
from ai.rag.context_builder import ContextBuilder
from ai.rag.retriever import Retriever

# JSON schema for the structured specialist output (§18.2, §35.2).
_GENERATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "cited_chunk_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "unanswerable": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["answer", "cited_chunk_ids", "unanswerable"],
}

_MALFORMED_REASON = "generation output was malformed or incomplete"


class GenerationResult(BaseModel):
    """Typed structured generation output (§18.2).

    ``cited_chunk_ids`` references retrieved chunks by id — citations are then
    assembled deterministically by the specialist (never free-form titles,
    §19.1). ``unanswerable`` triggers the no-answer policy (§20.4). ``model``
    and ``prompt_version`` record the provider model and the resolved prompt
    version for traceability (§34.6 — version + model recorded with each
    generated message).
    """

    answer: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    unanswerable: bool = False
    reason: str | None = None
    model: str | None = None
    prompt_version: str | None = None


class SpecialistAgent(ABC):
    """Stateless grounded-answer worker shared by Phase 1 specialists (§12.3).

    Subclasses configure the domain: ``AGENT_KEY``, ``DEFAULT_CATEGORIES``,
    ``DEFAULT_PROMPT_KEY``, and the fallback department. The pipeline methods
    (``retrieve`` / ``build_context`` / ``generate`` / ``assemble_citations``)
    mirror the §11.2 specialist-phase nodes.
    """

    AGENT_KEY: AgentKey
    DEFAULT_CATEGORIES: tuple[str, ...] = ()
    DEFAULT_PROMPT_KEY: str = ""
    DEFAULT_PROMPT_VERSION: str = "v1"
    FALLBACK_DEPARTMENT: str = "the university"

    def __init__(
        self,
        *,
        retriever: Retriever,
        gateway: LLMGateway,
        prompt_repository: PromptRepository | None = None,
        prompt_version: str | None = None,
        categories: Sequence[str] | None = None,
        top_k: int = 4,
        context_budget_tokens: int = 4096,
        context_builder: ContextBuilder | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        guardrails: SafetyGuardrails | None = None,
    ) -> None:
        self._retriever = retriever
        self._gateway = gateway
        repository = prompt_repository if prompt_repository is not None else default_repository()
        self.prompt: Prompt = self._resolve_prompt(repository, prompt_version)
        self.categories: tuple[str, ...] = tuple(
            categories if categories is not None else self.DEFAULT_CATEGORIES
        )
        self.top_k = top_k
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context_builder = context_builder or ContextBuilder(max_tokens=context_budget_tokens)
        self.guardrails = guardrails if guardrails is not None else default_guardrails()

    # --- configuration ------------------------------------------------------

    def _resolve_prompt(
        self, repository: PromptRepository, version: str | None
    ) -> Prompt:
        """Resolve this agent's registered versioned prompt (§13.1, §34).

        The prompt is resolved from the repository — never hardcoded — and its
        ownership metadata is validated: a prompt that is missing, requests an
        unsupported version, or is owned by a different agent fails fast with a
        ``ValueError`` instead of silently using the wrong prompt (§34.3, §34.6).
        Without ``version`` the repository returns the latest registered version
        (default version resolution, §34.6).
        """
        prompt = repository.get(self.DEFAULT_PROMPT_KEY, version)
        if prompt is None:
            label = f"@{version}" if version else ""
            raise ValueError(
                f"prompt '{self.DEFAULT_PROMPT_KEY}{label}' not found in the "
                "prompt repository"
            )
        if prompt.agent_key is not self.AGENT_KEY:
            raise ValueError(
                f"prompt '{prompt.key}@{prompt.version}' is owned by "
                f"{prompt.agent_key}, not {self.AGENT_KEY}"
            )
        return prompt

    # --- specialist-phase node behavior (§11.2) -----------------------------

    def retrieve(self, *, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Retrieve evidence scoped to this specialist's domain (§16.4)."""
        return self._retriever.retrieve(
            query=query,
            categories=self.categories,
            top_k=top_k or self.top_k,
        )

    def build_context(
        self,
        *,
        query: str,
        evidence: Sequence[RetrievedChunk] = (),
        message_history: Sequence[ChatTurn] = (),
        user_context: UserContext | None = None,
        user_document_texts: Sequence[str] = (),
    ) -> str:
        """Assemble the budgeted, labeled prompt context (§17.2)."""
        return self.context_builder.build(
            query=query,
            evidence=evidence,
            message_history=message_history,
            user_context=user_context,
            user_document_texts=user_document_texts,
        )

    def generate(
        self,
        *,
        query: str,
        context: str,
    ) -> GenerationResult:
        """Invoke grounded generation with structured output (§18.2).

        Provider failures surface as ``LLMError``; callers (``run``) degrade to
        a friendly fallback (§23.2). Malformed provider output degrades here to
        a safe no-answer result.
        """
        response = self._gateway.generate(
            system_prompt=self.prompt.text,
            user_prompt=context,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            json_schema=_GENERATION_SCHEMA,
        )
        return _parse_generation_json(
            response.content,
            model=response.model,
            prompt_version=self.prompt.version,
        )

    def assemble_citations(
        self,
        *,
        chunks: Sequence[RetrievedChunk],
        cited_chunk_ids: Sequence[str],
    ) -> list[Citation]:
        """Map cited chunk ids to citations in retrieval-score order (§19.3).

        Citations are derived only from retrieved chunks — a cited id that is
        not in the retrieved set is ignored, never invented (§19.1, §20.3).
        Duplicate chunk citations are de-duplicated (one citation per chunk per
        message, §19.3). Ordering is deterministic: retrieval score, highest
        first, with the retrieved position as the tie-break (§16.3/§16.5) — the
        order is identical on repeated execution and never follows the LLM's
        citation order. When duplicate chunk ids appear in the retrieved set
        the strongest (highest retrieval score) occurrence is kept. Scores are
        clamped to the 0..1 ``ai_sources_score_check`` contract (§19.4);
        non-finite scores degrade to 0.0 instead of failing validation.
        """
        by_id: dict[str, RetrievedChunk] = {}
        position: dict[str, int] = {}
        for index, entry in enumerate(chunks):
            existing = by_id.get(entry.chunk_id)
            if existing is None or entry.score > existing.score:
                by_id[entry.chunk_id] = entry
                position[entry.chunk_id] = index
        seen: set[str] = set()
        citations: list[Citation] = []
        for chunk_id in cited_chunk_ids:
            chunk = by_id.get(chunk_id)
            if chunk is None or chunk_id in seen:
                continue
            seen.add(chunk_id)
            citations.append(
                Citation(
                    title=chunk.title,
                    category=chunk.category,
                    snippet=chunk.snippet,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    relevance_score=_clamp_score(chunk.score),
                )
            )
        citations.sort(
            key=lambda citation: (
                -citation.relevance_score,
                position[citation.chunk_id or ""],
            )
        )
        return citations

    # --- full specialist pass (§11 specialist phase) ------------------------

    def run(
        self,
        *,
        query: str,
        message_history: Sequence[ChatTurn] = (),
        user_context: UserContext | None = None,
        user_document_texts: Sequence[str] = (),
    ) -> AgentOutput:
        """Execute the full specialist pass and return the agent output (§3.3).

        Input guardrail runs first: blocked input short-circuits to a safe
        fallback and never reaches retrieval or the LLM; empty/whitespace input
        is handled by the grounded no-answer path (§25-26). Then the pipeline
        retrieve → build context → generate → assemble citations runs; the
        generated answer is scanned by the output guardrail before delivery —
        blocked output is replaced with a safe fallback without citations
        (§26.4). Empty retrieval short-circuits to a grounded no-answer (no LLM
        call, §20.4); provider failures produce a friendly FALLBACK response
        (§23.2).
        """
        decision = self.guardrails.check_input(query)
        if decision.category is GuardrailCategory.EMPTY:
            return self._no_answer_output()
        if not decision.allowed:
            return AgentOutput(
                answer=decision.fallback or self._guardrail_blocked_text(),
                status=WorkflowStatus.COMPLETED,
            )
        try:
            chunks = self.retrieve(query=query)
            if not chunks:
                return self._no_answer_output()
            context = self.build_context(
                query=query,
                evidence=chunks,
                message_history=message_history,
                user_context=user_context,
                user_document_texts=user_document_texts,
            )
            result = self.generate(query=query, context=context)
            output_decision = self.guardrails.check_output(result.answer)
            if not output_decision.allowed:
                return AgentOutput(
                    answer=output_decision.fallback or self._guardrail_blocked_text(),
                    status=WorkflowStatus.COMPLETED,
                )
            citations = self.assemble_citations(
                chunks=chunks,
                cited_chunk_ids=result.cited_chunk_ids,
            )
            if result.unanswerable or not result.answer.strip():
                return AgentOutput(
                    answer=self.no_answer_text(),
                    citations=citations,
                    status=WorkflowStatus.COMPLETED,
                )
            return AgentOutput(
                answer=result.answer,
                citations=citations,
                status=WorkflowStatus.COMPLETED,
            )
        except LLMError:
            return AgentOutput(
                answer=self._fallback_text(),
                status=WorkflowStatus.FALLBACK,
            )

    # --- safe responses (§20.4, §25.3, §23.2) -------------------------------

    def no_answer_text(self) -> str:
        """Grounded "information unavailable" response with a referral (§20.4)."""
        return (
            "The information you requested is not available in the university "
            f"knowledge base at this time. Please contact {self.FALLBACK_DEPARTMENT} "
            "for official confirmation, and I can help you with related topics."
        )

    def _no_answer_output(self) -> AgentOutput:
        return AgentOutput(
            answer=self.no_answer_text(),
            status=WorkflowStatus.COMPLETED,
        )

    def _fallback_text(self) -> str:
        """Friendly, non-fabricating error response (§23.2)."""
        return (
            "I'm having trouble generating an answer right now. Please try "
            f"again in a moment, or contact {self.FALLBACK_DEPARTMENT} directly."
        )

    def _guardrail_blocked_text(self) -> str:
        """Generic safety fallback when a guardrail block has no rule fallback.

        Never exposes the internal detection reason (§26.3, §37).
        """
        return (
            "I can't help with that request. Please ask about admissions, "
            "examinations, or general university services."
        )


def _clamp_score(score: float) -> float:
    """Clamp a retrieval score to the 0..1 citation contract (§19.4).

    ``Citation.relevance_score`` is constrained to 0..1 to match the
    ``ai_sources_score_check`` database constraint (DATABASE_DESIGN.md §32.6).
    Non-finite scores (NaN/inf) cannot come from the Phase 9 retriever (§16.3
    validation) and would otherwise fail that constraint; they degrade to 0.0 —
    a safe citation, never a crash or a fabricated score.
    """
    if not math.isfinite(score):
        return 0.0
    return min(max(score, 0.0), 1.0)


def _parse_generation_json(
    content: str,
    *,
    model: str | None = None,
    prompt_version: str | None = None,
) -> GenerationResult:
    """Parse the strict-JSON generation output; malformed output degrades safely.

    The answer and cited chunk ids are always coerced to safe types; a missing
    or unparsable answer falls back to the no-answer path (never fabricated).
    ``model`` and ``prompt_version`` are preserved for traceability (§34.6 —
    version + model recorded with each generated message).
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return GenerationResult(
            answer="",
            unanswerable=True,
            reason=_MALFORMED_REASON,
            model=model,
            prompt_version=prompt_version,
        )
    if not isinstance(data, dict):
        return GenerationResult(
            answer="",
            unanswerable=True,
            reason=_MALFORMED_REASON,
            model=model,
            prompt_version=prompt_version,
        )

    raw_answer = data.get("answer")
    answer = str(raw_answer).strip() if raw_answer is not None else ""

    cited_ids: list[str] = []
    raw_ids = data.get("cited_chunk_ids")
    if isinstance(raw_ids, list):
        for value in raw_ids:
            if isinstance(value, str) and value.strip():
                cited_ids.append(value.strip())

    unanswerable = bool(data.get("unanswerable", not answer))

    raw_reason = data.get("reason")
    reason = str(raw_reason).strip() if raw_reason is not None else None
    return GenerationResult(
        answer=answer,
        cited_chunk_ids=cited_ids,
        unanswerable=unanswerable,
        reason=reason,
        model=model,
        prompt_version=prompt_version,
    )
