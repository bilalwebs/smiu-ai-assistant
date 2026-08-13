"""Versioned prompt assets for the AI service (AI_ARCHITECTURE.md §34).

Each module in this package owns one versioned prompt asset; ``default_prompts``
registers every asset into the default ``PromptRepository``. New agents add a
prompt module here and register it — no prompt text is ever embedded in an
agent, graph, or route (PROJECT_RULES.md Prompt Engineering Rules).
"""

from __future__ import annotations

from collections.abc import Iterable

from ai.prompts.repository import Prompt
from ai.prompts.versions.admission_v1 import prompt_v1 as admission_prompt_v1
from ai.prompts.versions.examination_v1 import prompt_v1 as examination_prompt_v1
from ai.prompts.versions.faq_v1 import prompt_v1 as faq_prompt_v1


def default_prompts() -> Iterable[Prompt]:
    """Register the current set of versioned prompt assets (§34)."""
    return (
        admission_prompt_v1(),
        examination_prompt_v1(),
        faq_prompt_v1(),
    )
