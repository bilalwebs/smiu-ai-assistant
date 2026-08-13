"""Agent Manager / registry (AI_ARCHITECTURE.md §3.4).

Purpose:
    Data-driven registry of every Phase 1 agent: key, display name, description
    (used for intent classification and routing), retrieval scope, and status.
    Routing chooses a specialist by the registered metadata + the routing table
    — there are no hardcoded routing branches (AI_ARCHITECTURE.md §3.4, §9.2).
    New agents are added by registry + routing-table entries, never by touching
    the workflow (AI_ARCHITECTURE.md §8 registration rules).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ai.core.state import AgentKey, IntentCategory

# Routing table: intent label -> agent key (AI_ARCHITECTURE.md §9.2 step 2).
# ``None`` means "no specialist — the Coordinator handles this intent" (e.g.
# out-of-scope topics route to safe/clarifying handling, §4.6, §9.5).
_ROUTING_TABLE: dict[IntentCategory, AgentKey | None] = {
    IntentCategory.ADMISSION: AgentKey.ADMISSION,
    IntentCategory.EXAMINATION: AgentKey.EXAMINATION,
    IntentCategory.FAQ: AgentKey.FAQ,
    IntentCategory.GENERAL: AgentKey.FAQ,
    IntentCategory.OUT_OF_SCOPE: None,
}


@dataclass(frozen=True)
class AgentInfo:
    """Registered agent metadata (AI_ARCHITECTURE.md §3.3-3.4).

    ``description`` is the routing-oriented capability summary consumed by the
    intent classifier for zero/few-shot classification (§9.1). ``prompt_version``
    references the versioned prompt asset owned by this agent (§13.1, §34).
    """

    key: AgentKey
    name: str
    description: str
    retrieval_categories: tuple[str, ...] = ()
    prompt_version: str = ""
    enabled: bool = True


def _phase1_agents() -> tuple[AgentInfo, ...]:
    return (
        AgentInfo(
            key=AgentKey.COORDINATOR,
            name="Coordinator",
            description=(
                "Entry point that detects intent, routes to a specialist, and "
                "handles ambiguous, unknown, or out-of-scope queries."
            ),
        ),
        AgentInfo(
            key=AgentKey.ADMISSION,
            name="Admission Agent",
            description=(
                "Admission requirements, eligibility criteria, required "
                "documents, merit policy and merit lists, admission process "
                "and deadlines, program intakes."
            ),
            retrieval_categories=("admission",),
            prompt_version="v1",
        ),
        AgentInfo(
            key=AgentKey.EXAMINATION,
            name="Examination Agent",
            description=(
                "Date sheets, results and result policy, admit cards, "
                "examination rules, improvement/supplementary policy."
            ),
            retrieval_categories=("examination",),
            prompt_version="v1",
        ),
        AgentInfo(
            key=AgentKey.FAQ,
            name="FAQ Agent",
            description=(
                "General university FAQs, departments and services, office "
                "timings, campus information, and contact details."
            ),
            retrieval_categories=("faq",),
            prompt_version="v1",
        ),
    )


class AgentRegistry:
    """Data-driven collection of agents plus the routing table (§3.4, §9.2)."""

    def __init__(
        self,
        agents: Iterable[AgentInfo] | None = None,
        routing_table: dict[IntentCategory, AgentKey | None] | None = None,
    ) -> None:
        self._agents: dict[AgentKey, AgentInfo] = {}
        for agent in agents or ():
            self.register(agent)
        self._routing_table: dict[IntentCategory, AgentKey | None] = (
            dict(routing_table) if routing_table is not None else dict(_ROUTING_TABLE)
        )

    def register(self, agent: AgentInfo) -> None:
        if agent.key in self._agents:
            raise ValueError(f"Agent already registered: {agent.key}")
        self._agents[agent.key] = agent

    def get(self, key: AgentKey) -> AgentInfo | None:
        return self._agents.get(key)

    def entries(self) -> list[AgentInfo]:
        return list(self._agents.values())

    def enabled_agents(self) -> list[AgentInfo]:
        return [agent for agent in self._agents.values() if agent.enabled]

    def descriptions(self) -> str:
        """Capability descriptions consumed by the intent classifier (§9.1)."""
        lines = [
            f"- {agent.key.value}: {agent.description}" for agent in self.enabled_agents()
        ]
        return "\n".join(lines)

    def resolve(self, intent: IntentCategory) -> AgentKey | None:
        """Map an intent to an agent via the routing table (§9.2 step 2).

        Returns ``None`` when no specialist is mapped or the target agent is
        disabled — the Coordinator then handles the turn (clarify/fallback).
        """
        key = self._routing_table.get(intent)
        if key is None:
            return None
        agent = self._agents.get(key)
        if agent is None or not agent.enabled:
            return None
        return key

    def categories_for(self, key: AgentKey) -> tuple[str, ...]:
        """Retrieval categories scoped to an agent's knowledge domain (§4.2)."""
        agent = self._agents.get(key)
        return agent.retrieval_categories if agent is not None else ()


_default_registry: AgentRegistry | None = None


def default_registry() -> AgentRegistry:
    """Return the cached Phase 1 registry (AI_ARCHITECTURE.md §3.2)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry(_phase1_agents())
    return _default_registry
