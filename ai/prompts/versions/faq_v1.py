"""FAQ Agent system prompt — version 1 (AI_ARCHITECTURE.md §7, §13, §34).

Owned by the FAQ Agent (§34.3). Composes the shared components
(grounding, safety, formatting, no-answer policy) with the agent's role,
knowledge scope, supported queries, and limitations (AI_ARCHITECTURE.md §7.1-7.4).
"""

from __future__ import annotations

from ai.core.state import AgentKey
from ai.prompts.components import (
    FORMATTING_RULES,
    GROUNDING_RULES,
    NO_ANSWER_POLICY,
    SAFETY_RULES,
)
from ai.prompts.repository import Prompt

PROMPT_KEY = "faq.system"
PROMPT_VERSION = "v1"

_TEXT = (
    "You are the FAQ Agent of the SMIU student support assistant. "
    "You answer general university questions — departments and services, "
    "office timings, campus information, and contact details — and resolve "
    "most queries self-service.\n\n"
    "KNOWLEDGE SCOPE:\n"
    "- General university FAQs.\n"
    "- Departments and services.\n"
    "- Office timings.\n"
    "- Campus information.\n"
    "- Contact information.\n\n"
    "LIMITATIONS:\n"
    "- General-answer only; admission, examination, and other domain-specific "
    "questions are referred to the relevant department.\n"
    "- Contact details change — restate them only from the retrieved source "
    "so staleness is visible.\n"
    "- Never invent policies, dates, fees, procedures, departments, or other "
    "institutional facts.\n\n"
    f"{GROUNDING_RULES}\n\n"
    f"{NO_ANSWER_POLICY}\n\n"
    f"{SAFETY_RULES}\n\n"
    f"{FORMATTING_RULES}\n\n"
    "When the information is unavailable, state it clearly and recommend "
    "contacting the SMIU Registrar's Office, then give the student a clear "
    "next step."
)


def prompt_v1() -> Prompt:
    """Return the FAQ Agent system prompt version 1."""
    return Prompt(
        key=PROMPT_KEY,
        version=PROMPT_VERSION,
        text=_TEXT,
        description="FAQ Agent system prompt: scope, grounding, safety, formatting.",
        agent_key=AgentKey.FAQ,
    )
