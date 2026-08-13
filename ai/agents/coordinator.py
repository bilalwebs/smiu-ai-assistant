"""Coordinator Agent (AI_ARCHITECTURE.md §4, §9).

Purpose:
    The single external entry point of the workflow. Responsibilities (§4.1):
      - intent analysis: classify the query into a typed routing signal (§9.1),
      - routing: select a specialist from the Agent Manager registry (§9.2),
      - fallback: leave ambiguous, unknown, or out-of-scope turns unresolved so
        the workflow returns a clarifying/fallback turn instead of forcing a
        specialist (§4.6, §9.4-9.5, §11.3).

    The Coordinator owns no retrieval, no generation, and no persistence — the
    specialist phase and the response builder handle those (§3.5). Conversation
    context is passed into intent analysis so follow-ups route correctly (§4.3,
    §9.3 conversation continuity).
"""

from __future__ import annotations

from typing import TypeAlias

from ai.agents.intent_classifier import (
    IntentClassifier,
    IntentResult,
    LLMIntentClassifier,
    RuleBasedIntentClassifier,
)
from ai.agents.registry import AgentRegistry, default_registry
from ai.core.config import Settings
from ai.core.state import AgentKey, ChatTurn, IntentCategory, RoutingSignal, UserContext
from ai.gateway.base import LLMGateway, redact_secrets
from ai.gateway.factory import build_llm_gateway

# Minimum confidence for a routing decision; below it the turn is treated as
# ambiguous and routed to clarification (AI_ARCHITECTURE.md §9.4, §11.3).
DEFAULT_CONFIDENCE_THRESHOLD = 0.6

# Domain intents that can carry a low-confidence signal; the clarifying turn
# may then offer the nearest specialist by name (§9.4). GENERAL (unknown) and
# OUT_OF_SCOPE are handled by the generic/scope-boundary clarifying text.
_CLARIFIABLE_DOMAINS: tuple[IntentCategory, ...] = (
    IntentCategory.ADMISSION,
    IntentCategory.EXAMINATION,
    IntentCategory.FAQ,
)


def _clarification_text(topics: str, *, nearest_label: str | None = None) -> str:
    """Grounded clarifying turn listing the suggested intents (§9.4-9.5).

    Optionally names the nearest specialist when the low-confidence signal
    points at a domain (§9.4). Student-facing and safe: no routing internals,
    confidence values, or raw reasons are ever exposed (§26.3, §37).
    """
    if nearest_label is not None:
        return (
            "Could you clarify your question? It sounds like you might be "
            f"asking about {nearest_label}. I can help you with:\n{topics}\n\n"
            "Please rephrase your question so I can point you to the right help."
        )
    return (
        "I'm not sure which area your question falls under. I can help you "
        f"with:\n{topics}\n\nCould you rephrase your question, or pick one of "
        "the topics above?"
    )


def _out_of_scope_text(topics: str) -> str:
    """Scope-boundary response with a department referral (§4.6, §9.5)."""
    return (
        "I'm here to help with university topics such as admissions, "
        "examinations, and general university services. That request is outside "
        "what I can assist with. For further help, please contact the "
        f"university directly.\n\nHere is what I can help with:\n{topics}"
    )

History: TypeAlias = list[ChatTurn] | None
UserCtx: TypeAlias = UserContext | None


class CoordinatorAgent:
    """Entry-point agent: intent analysis + specialist selection (§4.1)."""

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        classifier: IntentClassifier | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.registry = registry if registry is not None else default_registry()
        self.classifier = classifier if classifier is not None else RuleBasedIntentClassifier()
        self.confidence_threshold = confidence_threshold

    def detect_intent(
        self,
        user_query: str,
        *,
        message_history: History = None,
        user_context: UserCtx = None,
    ) -> RoutingSignal:
        """Classify the query into a typed routing signal (§4.1, §9.1).

        The signal always starts with the Coordinator as the tentative agent —
        specialist selection is the routing step's job (§9.2, §11.2). Ambiguous,
        unknown, or out-of-scope turns keep the Coordinator agent so the router
        edge returns a clarifying turn rather than a forced route (§9.4-9.5).
        A classifier failure never crashes the run: it degrades to a
        low-confidence GENERAL signal so the workflow returns a safe clarifying
        turn (§23.2).
        """
        try:
            result = self.classifier.classify(
                user_query=user_query,
                agent_descriptions=self.registry.descriptions(),
                message_history=message_history,
                user_context=user_context,
            )
        # A classifier crash must never take down the run: degrade to a safe
        # low-confidence signal so the workflow returns a clarifying turn.
        except Exception as exc:
            result = IntentResult(
                intent=IntentCategory.GENERAL,
                confidence=0.0,
                reason=f"intent detection failed: {redact_secrets(str(exc))}",
            )
        return RoutingSignal(
            intent=result.intent,
            selected_agent=AgentKey.COORDINATOR,
            confidence=result.confidence,
            secondary_intents=result.secondary_intents,
            reason=result.reason,
        )

    def route(self, signal: RoutingSignal) -> AgentKey | None:
        """Select the specialist for a routing signal (§9.2, §11.2).

        Returns the agent key when the intent is resolvable and confident
        enough; ``None`` when the signal is ambiguous (below threshold), unknown
        (no routing-table entry), or out-of-scope — the Coordinator then handles
        the turn (§4.6, §9.4).
        """
        if signal.intent is IntentCategory.OUT_OF_SCOPE:
            return None
        if signal.confidence < self.confidence_threshold:
            return None
        return self.registry.resolve(signal.intent)

    def needs_clarification(self, signal: RoutingSignal) -> bool:
        """True when a turn cannot be routed and must clarify (§9.4)."""
        return self.route(signal) is None

    def clarify(self, signal: RoutingSignal | None) -> str:
        """Build the grounded clarifying turn (§4.6, §9.4-9.5, §11.3).

        The clarifying response is deterministic and data-driven: the help
        topics are built from the registered agent names/descriptions, never
        hardcoded branches, and the Coordinator never selects a specialist here
        (§9.5 "the Coordinator never guesses"). Response shape per the routing
        signal (§4.6, §9.4):

        - missing signal (unknown/undetectable): generic clarifying response
          listing what the assistant can help with (§9.4 "suggested intents",
          §9.5),
        - out-of-scope intent: scope boundary + department referral (§4.6,
          §9.5), never a misroute,
        - low-confidence domain intent: ask for clarification and offer the
          nearest specialist by name (§9.4 "optionally offer the nearest
          specialist" — offered in text only, never routed).

        The raw routing reason is never surfaced (internal traceability only,
        §9.4, §37) — the response exposes no detection internals or secrets.
        """
        topics = self._help_topics()
        if signal is None:
            return _clarification_text(topics)
        if signal.intent is IntentCategory.OUT_OF_SCOPE:
            return _out_of_scope_text(topics)
        if signal.intent in _CLARIFIABLE_DOMAINS:
            nearest = self.registry.resolve(signal.intent)
            if nearest is not None:
                agent = self.registry.get(nearest)
                label = agent.name if agent is not None else nearest.value
                return _clarification_text(topics, nearest_label=label)
        return _clarification_text(topics)

    def _help_topics(self) -> str:
        """Registered help topics for the clarifying response (§9.4-9.5).

        Grounded in the registry: every enabled non-Coordinator agent becomes a
        suggested intent, so the list stays aligned with the available
        specialists without hardcoding routing branches (§3.4, §8).
        """
        agents = [
            agent
            for agent in self.registry.enabled_agents()
            if agent.key is not AgentKey.COORDINATOR
        ]
        return "\n".join(f"- {agent.name}: {agent.description}" for agent in agents)


def create_coordinator(
    *,
    registry: AgentRegistry | None = None,
    classifier: IntentClassifier | None = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> CoordinatorAgent:
    """Build a Coordinator with explicit or default dependencies.

    The default classifier is the deterministic rule-based implementation, so
    constructing a Coordinator never requires API keys or external services.
    """
    return CoordinatorAgent(
        registry=registry,
        classifier=classifier,
        confidence_threshold=confidence_threshold,
    )


def create_llm_coordinator(
    *,
    settings: Settings,
    registry: AgentRegistry | None = None,
    gateway: LLMGateway | None = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> CoordinatorAgent:
    """Build a Coordinator backed by the LLM gateway (§4.1, §35.1).

    The gateway is built from ``settings`` unless injected (tests inject a fake
    gateway so the suite runs fully offline). The Coordinator itself stays
    provider-agnostic — it only sees the ``IntentClassifier`` protocol.
    """
    resolved_gateway = gateway if gateway is not None else build_llm_gateway(settings)
    classifier = LLMIntentClassifier(gateway=resolved_gateway)
    return CoordinatorAgent(
        registry=registry,
        classifier=classifier,
        confidence_threshold=confidence_threshold,
    )
