"""Versioned prompt repository (AI_ARCHITECTURE.md §13.1, §34).

Purpose:
    Prompts are versioned assets, owned per agent, stored exclusively in
    ``ai/prompts/`` and never hardcoded in agents or routes (PROJECT_RULES.md
    Prompt Engineering Rules). The repository is the single access point:
    agents request their prompt by key and version; the text is composed from
    the shared components (AI_ARCHITECTURE.md §34.6-34.7).

Versioning (§34.6):
    - every prompt carries a version id recorded with each generated message
      for traceability and reproducibility,
    - old versions remain queryable; ``get(key, version=None)`` returns the
      latest registered version,
    - ``agent_key`` records the owning agent (§34.3).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ai.core.state import AgentKey


@dataclass(frozen=True)
class Prompt:
    """A versioned prompt asset (AI_ARCHITECTURE.md §34)."""

    key: str
    version: str
    text: str
    description: str = ""
    agent_key: AgentKey | None = None


class PromptRepository:
    """Registry of versioned prompt assets (§34.6).

    Prompt order within a key is registration order; the last registered
    version is the latest (used by ``get(key)``).
    """

    def __init__(self, prompts: Iterable[Prompt] = ()) -> None:
        self._by_key: dict[str, list[Prompt]] = {}
        for prompt in prompts:
            self.add(prompt)

    def add(self, prompt: Prompt) -> None:
        if not prompt.key or not prompt.version:
            raise ValueError("prompt key and version are required")
        versions = self._by_key.setdefault(prompt.key, [])
        if any(existing.version == prompt.version for existing in versions):
            raise ValueError(f"duplicate prompt version: {prompt.key}@{prompt.version}")
        versions.append(prompt)

    def get(self, key: str, version: str | None = None) -> Prompt | None:
        """Return a prompt by key; without ``version``, the latest one (§34.6)."""
        versions = self._by_key.get(key)
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for prompt in reversed(versions):
            if prompt.version == version:
                return prompt
        return None

    def versions(self, key: str) -> list[str]:
        return [prompt.version for prompt in self._by_key.get(key, ())]

    def for_agent(self, agent_key: AgentKey) -> list[Prompt]:
        return [
            prompt
            for versions in self._by_key.values()
            for prompt in versions
            if prompt.agent_key is agent_key
        ]


_default_repository: PromptRepository | None = None


def default_repository() -> PromptRepository:
    """Return the cached default repository with the registered prompt assets.

    Built lazily from ``ai.prompts.versions.default_prompts()`` so importing
    the repository never triggers prompt-module imports.
    """
    global _default_repository
    if _default_repository is None:
        from ai.prompts.versions import default_prompts

        _default_repository = PromptRepository(default_prompts())
    return _default_repository


def clear_default_repository() -> None:
    """Drop the cached default repository; used by tests to reset state."""
    global _default_repository
    _default_repository = None
