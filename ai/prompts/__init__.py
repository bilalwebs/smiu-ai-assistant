"""Versioned prompt assets for the AI service (AI_ARCHITECTURE.md §13, §34).

Prompts are versioned assets stored exclusively in this package — never in
agents, graphs, or routes (PROJECT_RULES.md Prompt Engineering Rules). The
``PromptRepository`` is the single access point; shared components live in
``ai.prompts.components`` and are composed per agent (AI_ARCHITECTURE.md §34.7).
"""

from ai.prompts.repository import (
    Prompt,
    PromptRepository,
    clear_default_repository,
    default_repository,
)

__all__ = [
    "Prompt",
    "PromptRepository",
    "clear_default_repository",
    "default_repository",
]
