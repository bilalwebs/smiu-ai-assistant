"""Examination Agent (AI_ARCHITECTURE.md §6).

Purpose:
    The examination specialist: answers examination queries grounded in the
    examination knowledge base — date sheets, results and result policy, admit
    cards, examination rules, and improvement policy (§6.1-6.3). It is a
    stateless specialist worker (§12.3) built on the shared specialist
    machinery: retrieve → build context → generate → citations
    (AI_ARCHITECTURE.md §11.2).

Behavior:
    - retrieval is scoped to the ``examination`` knowledge category (§6.2, §16.4),
    - answers are generated only from retrieved evidence (§20.1); no evidence
      produces a grounded "information unavailable" response (§20.4),
    - individual result changes are never handled by the agent; confirmation
      or correction needs are escalated to the Examination Department
      (§6.4, §25.1; BACKEND_ARCHITECTURE.md §32.3),
    - provisional/pre-official data is never invented — only published
      information is answered (§6.4).
"""

from __future__ import annotations

from collections.abc import Sequence

from ai.agents.base import SpecialistAgent
from ai.core.config import Settings
from ai.core.state import AgentKey
from ai.gateway.base import LLMGateway
from ai.gateway.factory import build_llm_gateway
from ai.prompts.versions.examination_v1 import PROMPT_KEY
from ai.rag.retriever import Retriever

_EXAMINATION_CATEGORIES = ("examination",)


class ExaminationAgent(SpecialistAgent):
    """Examination specialist worker (AI_ARCHITECTURE.md §6, §12.3)."""

    AGENT_KEY = AgentKey.EXAMINATION
    DEFAULT_CATEGORIES = _EXAMINATION_CATEGORIES
    DEFAULT_PROMPT_KEY = PROMPT_KEY
    FALLBACK_DEPARTMENT = "the SMIU Examination Department"


def create_examination_agent(
    *,
    settings: Settings,
    retriever: Retriever,
    gateway: LLMGateway | None = None,
    prompt_repository=None,
    categories: Sequence[str] | None = None,
) -> ExaminationAgent:
    """Build the Examination Agent with explicit or default dependencies.

    The gateway is built from ``settings`` unless injected (tests inject a fake
    gateway so the suite runs fully offline). Retrieval is always injected —
    Phase 9 supplies the FAISS-backed retriever; tests supply a fake.
    """
    resolved_gateway = gateway if gateway is not None else build_llm_gateway(settings)
    return ExaminationAgent(
        retriever=retriever,
        gateway=resolved_gateway,
        prompt_repository=prompt_repository,
        categories=categories,
        top_k=settings.rag_top_k,
        context_budget_tokens=settings.context_budget_tokens,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


__all__ = ["ExaminationAgent", "create_examination_agent"]
