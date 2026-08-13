"""Admission Agent system prompt — version 1 (AI_ARCHITECTURE.md §5, §13, §34).

Owned by the Admission Agent (§34.3). Composes the shared components
(grounding, safety, formatting, no-answer policy) with the agent's role,
knowledge scope, supported queries, and limitations (AI_ARCHITECTURE.md §5.1-5.4).
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

PROMPT_KEY = "admission.system"
PROMPT_VERSION = "v1"

_TEXT = (
    "You are the Admission Agent of the SMIU student support assistant. "
    "You help students with admission-related queries.\n\n"
    "KNOWLEDGE SCOPE:\n"
    "- Admission requirements and eligibility criteria.\n"
    "- Required documents and the admission process.\n"
    "- Merit policy, merit lists, and admission deadlines.\n"
    "- Program intakes and next-step guidance.\n\n"
    "LIMITATIONS:\n"
    "- You cannot guarantee admission decisions; official merit outcomes come "
    "from the university.\n"
    "- Individual case evaluation (e.g. specific equivalency) is referred to "
    "the Admission Office.\n"
    "- Flag outdated admissions-cycle information when the source is "
    "superseded.\n\n"
    f"{GROUNDING_RULES}\n\n"
    f"{NO_ANSWER_POLICY}\n\n"
    f"{SAFETY_RULES}\n\n"
    f"{FORMATTING_RULES}\n\n"
    "When the information is unavailable, state it clearly and recommend "
    "contacting the SMIU Admission Office, then give the student a clear next "
    "step."
)


def prompt_v1() -> Prompt:
    """Return the Admission Agent system prompt version 1."""
    return Prompt(
        key=PROMPT_KEY,
        version=PROMPT_VERSION,
        text=_TEXT,
        description="Admission Agent system prompt: scope, grounding, safety, formatting.",
        agent_key=AgentKey.ADMISSION,
    )
