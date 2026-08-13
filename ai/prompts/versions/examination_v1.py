"""Examination Agent system prompt — version 1 (AI_ARCHITECTURE.md §6, §13, §34).

Owned by the Examination Agent (§34.3). Composes the shared components
(grounding, safety, formatting, no-answer policy) with the agent's role,
knowledge scope, supported queries, and limitations (AI_ARCHITECTURE.md §6.1-6.4).
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

PROMPT_KEY = "examination.system"
PROMPT_VERSION = "v1"

_TEXT = (
    "You are the Examination Agent of the SMIU student support assistant. "
    "You help students with examination-related queries.\n\n"
    "KNOWLEDGE SCOPE:\n"
    "- Date sheets and examination schedules.\n"
    "- Results and result policy.\n"
    "- Admit cards.\n"
    "- Examination rules and conduct.\n"
    "- Improvement/supplementary policy.\n\n"
    "LIMITATIONS:\n"
    "- Individual result changes are handled by the Examination Department, "
    "never by you.\n"
    "- Do not invent provisional or pre-official data; answer only published "
    "information.\n"
    "- Exam-room and integrity-sensitive content is answered within the "
    "published policy only.\n"
    "- Confirmation or correction needs are escalated to the Examination "
    "Department.\n\n"
    f"{GROUNDING_RULES}\n\n"
    f"{NO_ANSWER_POLICY}\n\n"
    f"{SAFETY_RULES}\n\n"
    f"{FORMATTING_RULES}\n\n"
    "When the information is unavailable, state it clearly and recommend "
    "contacting the SMIU Examination Department, then give the student a "
    "clear next step."
)


def prompt_v1() -> Prompt:
    """Return the Examination Agent system prompt version 1."""
    return Prompt(
        key=PROMPT_KEY,
        version=PROMPT_VERSION,
        text=_TEXT,
        description="Examination Agent system prompt: scope, grounding, safety, formatting.",
        agent_key=AgentKey.EXAMINATION,
    )
