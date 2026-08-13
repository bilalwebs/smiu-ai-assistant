"""FAQ Agent (AI_ARCHITECTURE.md §7).

Purpose:
    The general university information specialist: answers general university
    questions grounded in the FAQ and general knowledge base — departments and
    services, office timings, campus information, and contact details
    (§7.1-7.3). It is a stateless specialist worker (§12.3) built on the shared
    specialist machinery: retrieve → build context → generate → citations
    (AI_ARCHITECTURE.md §11.2).

Behavior:
    - retrieval is scoped to the ``faq`` knowledge category (§7.2, §16.4),
    - answers are generated only from retrieved evidence (§20.1); no evidence
      produces a grounded "information unavailable" response (§20.4),
    - general-answer only: admission/examination and other domain-specific
      questions are never answered from model memory and are referred to the
      relevant department (§7.4, §25.1),
    - contact details are only ever restated from a cited source so staleness
      stays visible (§7.4); policies, dates, fees, procedures, departments, or
      other institutional facts are never fabricated.
"""

from __future__ import annotations

from collections.abc import Sequence

from ai.agents.base import SpecialistAgent
from ai.core.config import Settings
from ai.core.state import AgentKey
from ai.gateway.base import LLMGateway
from ai.gateway.factory import build_llm_gateway
from ai.prompts.versions.faq_v1 import PROMPT_KEY
from ai.rag.retriever import Retriever

_FAQ_CATEGORIES = ("faq",)


class FAQAgent(SpecialistAgent):
    """FAQ specialist worker (AI_ARCHITECTURE.md §7, §12.3)."""

    AGENT_KEY = AgentKey.FAQ
    DEFAULT_CATEGORIES = _FAQ_CATEGORIES
    DEFAULT_PROMPT_KEY = PROMPT_KEY
    FALLBACK_DEPARTMENT = "the SMIU Registrar's Office"


def create_faq_agent(
    *,
    settings: Settings,
    retriever: Retriever,
    gateway: LLMGateway | None = None,
    prompt_repository=None,
    categories: Sequence[str] | None = None,
) -> FAQAgent:
    """Build the FAQ Agent with explicit or default dependencies.

    The gateway is built from ``settings`` unless injected (tests inject a fake
    gateway so the suite runs fully offline). Retrieval is always injected —
    Phase 9 supplies the FAISS-backed retriever; tests supply a fake.
    """
    resolved_gateway = gateway if gateway is not None else build_llm_gateway(settings)
    return FAQAgent(
        retriever=retriever,
        gateway=resolved_gateway,
        prompt_repository=prompt_repository,
        categories=categories,
        top_k=settings.rag_top_k,
        context_budget_tokens=settings.context_budget_tokens,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


__all__ = ["FAQAgent", "create_faq_agent"]
