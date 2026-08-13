"""Admission Agent (AI_ARCHITECTURE.md §5).

Purpose:
    The admission specialist: answers admission queries grounded in the
    admission knowledge base — requirements, eligibility, required documents,
    merit policy/lists, the admission process and deadlines (§5.1-5.3).
    It is a stateless specialist worker (§12.3) built on the shared
    specialist machinery: retrieve → build context → generate → citations
    (AI_ARCHITECTURE.md §11.2).

Behavior:
    - retrieval is scoped to the ``admission`` knowledge category (§5.2, §16.4),
    - answers are generated only from retrieved evidence (§20.1); no evidence
      produces a grounded "information unavailable" response (§20.4),
    - individual admission decisions are never guaranteed; case evaluation is
      referred to the Admission Office (§5.4, §25.1).
"""

from __future__ import annotations

from collections.abc import Sequence

from ai.agents.base import SpecialistAgent
from ai.core.config import Settings
from ai.core.state import AgentKey
from ai.gateway.base import LLMGateway
from ai.gateway.factory import build_llm_gateway
from ai.prompts.versions.admission_v1 import PROMPT_KEY
from ai.rag.retriever import Retriever

_ADMISSION_CATEGORIES = ("admission",)


class AdmissionAgent(SpecialistAgent):
    """Admission specialist worker (AI_ARCHITECTURE.md §5, §12.3)."""

    AGENT_KEY = AgentKey.ADMISSION
    DEFAULT_CATEGORIES = _ADMISSION_CATEGORIES
    DEFAULT_PROMPT_KEY = PROMPT_KEY
    FALLBACK_DEPARTMENT = "the SMIU Admission Office"


def create_admission_agent(
    *,
    settings: Settings,
    retriever: Retriever,
    gateway: LLMGateway | None = None,
    prompt_repository=None,
    categories: Sequence[str] | None = None,
) -> AdmissionAgent:
    """Build the Admission Agent with explicit or default dependencies.

    The gateway is built from ``settings`` unless injected (tests inject a fake
    gateway so the suite runs fully offline). Retrieval is always injected —
    Phase 9 supplies the FAISS-backed retriever; tests supply a fake.
    """
    resolved_gateway = gateway if gateway is not None else build_llm_gateway(settings)
    return AdmissionAgent(
        retriever=retriever,
        gateway=resolved_gateway,
        prompt_repository=prompt_repository,
        categories=categories,
        top_k=settings.rag_top_k,
        context_budget_tokens=settings.context_budget_tokens,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


__all__ = ["AdmissionAgent", "create_admission_agent"]
