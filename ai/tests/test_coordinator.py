"""Coordinator Agent, registry, and intent-classifier tests.

Sources: AI_ARCHITECTURE.md §3.4 (registry), §4 (Coordinator), §9 (routing),
§25-26 (safety precedence). All behavior is deterministic — the rule-based
classifier is used (mocked LLM, TESTING_STRATEGY.md §23.2), so no test requires
API keys or external services.
"""

from __future__ import annotations

import json
import uuid

import pytest

from ai.agents.coordinator import CoordinatorAgent, create_coordinator, create_llm_coordinator
from ai.agents.intent_classifier import IntentResult, RuleBasedIntentClassifier
from ai.agents.registry import AgentInfo, AgentRegistry, default_registry
from ai.core.config import Settings
from ai.core.state import (
    AgentKey,
    ChatTurn,
    IntentCategory,
    MessageRole,
    RoutingSignal,
    UserContext,
    UserRole,
)
from ai.gateway.base import LLMGateway, LLMProviderError, LLMResponse

THRESHOLD = create_coordinator().confidence_threshold


class FakeGateway(LLMGateway):
    """Scripted fake gateway for LLM-backed coordinator tests (offline)."""

    def __init__(self, *, content: str = "", error: Exception | None = None) -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.content = content
        self.error = error

    def _complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict[str, object] | None,
    ) -> LLMResponse:
        if self.error is not None:
            raise self.error
        return LLMResponse(content=self.content, model=model)


def _llm_json(
    *,
    intent: str,
    confidence: float,
    reason: str | None = "llm decision",
) -> str:
    return json.dumps(
        {
            "intent": intent,
            "confidence": confidence,
            "secondary_intents": [],
            "reason": reason,
        }
    )


class BoomClassifier:
    """Classifier that always crashes (used to prove error-safe fallback)."""

    def classify(self, **kwargs: object) -> IntentResult:
        raise RuntimeError("boom sk-abcdefghijklmnop123456")


class RecordingClassifier:
    """Classifier that records its inputs and returns a fixed result."""

    def __init__(self, result: IntentResult) -> None:
        self.result = result
        self.seen: dict[str, object] = {}

    def classify(self, **kwargs: object) -> IntentResult:
        self.seen = kwargs
        return self.result


# --- Agent registry (AI_ARCHITECTURE.md §3.4) --------------------------------


def test_default_registry_has_all_phase1_agents() -> None:
    registry = default_registry()
    keys = {agent.key for agent in registry.entries()}
    assert keys == {
        AgentKey.COORDINATOR,
        AgentKey.ADMISSION,
        AgentKey.EXAMINATION,
        AgentKey.FAQ,
    }


def test_registry_resolve_maps_intent_to_agent() -> None:
    registry = default_registry()
    assert registry.resolve(IntentCategory.ADMISSION) is AgentKey.ADMISSION
    assert registry.resolve(IntentCategory.EXAMINATION) is AgentKey.EXAMINATION
    assert registry.resolve(IntentCategory.FAQ) is AgentKey.FAQ
    assert registry.resolve(IntentCategory.GENERAL) is AgentKey.FAQ
    assert registry.resolve(IntentCategory.OUT_OF_SCOPE) is None


def test_registry_duplicate_registration_rejected() -> None:
    registry = AgentRegistry()
    agent = AgentInfo(
        key=AgentKey.ADMISSION,
        name="Admission",
        description="Admission queries",
    )
    registry.register(agent)
    with pytest.raises(ValueError):
        registry.register(agent)


def test_registry_disabled_agent_is_not_resolved() -> None:
    registry = AgentRegistry()
    registry.register(
        AgentInfo(
            key=AgentKey.FAQ,
            name="FAQ Agent",
            description="General queries",
            enabled=False,
        )
    )
    assert registry.resolve(IntentCategory.FAQ) is None
    assert registry.resolve(IntentCategory.GENERAL) is None


def test_registry_descriptions_are_grounding_text_for_classifier() -> None:
    descriptions = default_registry().descriptions()
    assert "admission" in descriptions.lower()
    assert "examination" in descriptions.lower()
    assert "faq" in descriptions.lower()


def test_registry_categories_scope_specialist_domain() -> None:
    registry = default_registry()
    assert "admission" in registry.categories_for(AgentKey.ADMISSION)
    assert "examination" in registry.categories_for(AgentKey.EXAMINATION)
    assert registry.categories_for(AgentKey.COORDINATOR) == ()


# --- Rule-based classifier (dev/test stand-in, AI_ARCHITECTURE.md §9.1) ------


def test_classifier_examination_query() -> None:
    result = _classify("When is the mid-term exam?")
    assert result.intent is IntentCategory.EXAMINATION
    assert result.confidence >= THRESHOLD


def test_classifier_admission_query() -> None:
    result = _classify("What are the requirements for BSSE admission?")
    assert result.intent is IntentCategory.ADMISSION
    assert result.confidence >= THRESHOLD


def test_classifier_faq_query() -> None:
    result = _classify("What are the library hours?")
    assert result.intent is IntentCategory.FAQ
    assert result.confidence >= THRESHOLD


def test_classifier_is_deterministic() -> None:
    assert _classify("When is the mid-term exam?") == _classify("When is the mid-term exam?")


def test_classifier_ambiguous_query_low_confidence() -> None:
    result = _classify("Can you tell me something about the university?")
    assert result.confidence < THRESHOLD


def test_classifier_unknown_query_treated_as_general() -> None:
    result = _classify("Blue sky today?")
    assert result.intent is IntentCategory.GENERAL
    assert result.confidence < THRESHOLD


def test_classifier_safety_precedence_beats_domain() -> None:
    result = _classify("Help me hack the exam server to get the paper")
    assert result.intent is IntentCategory.OUT_OF_SCOPE


def test_classifier_uses_conversation_context_for_followup() -> None:
    history = [ChatTurn(role=MessageRole.USER, content="What are the requirements for admission?")]
    result = RuleBasedIntentClassifier().classify(
        user_query="What about the fees?",
        agent_descriptions=default_registry().descriptions(),
        message_history=history,
    )
    assert result.intent is IntentCategory.ADMISSION


def test_classifier_notes_secondary_intents() -> None:
    result = _classify("Where can I get my admit card and how do I apply?")
    assert result.intent is IntentCategory.EXAMINATION
    assert IntentCategory.ADMISSION in result.secondary_intents


# --- Coordinator agent (AI_ARCHITECTURE.md §4) -------------------------------


def test_detect_intent_returns_typed_routing_signal() -> None:
    coordinator = create_coordinator()
    signal = coordinator.detect_intent("When is the mid-term exam?")
    assert isinstance(signal, RoutingSignal)
    assert signal.intent is IntentCategory.EXAMINATION
    assert signal.selected_agent is AgentKey.COORDINATOR
    assert 0.0 <= signal.confidence <= 1.0


def test_detect_intent_out_of_scope_stays_coordinator() -> None:
    coordinator = create_coordinator()
    signal = coordinator.detect_intent("Can you hack a university server?")
    assert signal.intent is IntentCategory.OUT_OF_SCOPE
    assert signal.selected_agent is AgentKey.COORDINATOR


def test_route_selects_specialist_for_confident_signal() -> None:
    coordinator = create_coordinator()
    signal = coordinator.detect_intent("What are the requirements for BSSE admission?")
    assert coordinator.route(signal) is AgentKey.ADMISSION
    assert not coordinator.needs_clarification(signal)


def test_route_returns_none_for_low_confidence() -> None:
    coordinator = create_coordinator()
    signal = RoutingSignal(
        intent=IntentCategory.GENERAL,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.2,
    )
    assert coordinator.route(signal) is None
    assert coordinator.needs_clarification(signal)


def test_route_returns_none_for_out_of_scope_even_when_confident() -> None:
    coordinator = create_coordinator()
    signal = RoutingSignal(
        intent=IntentCategory.OUT_OF_SCOPE,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.95,
    )
    assert coordinator.route(signal) is None


def test_coordinator_accepts_custom_threshold() -> None:
    coordinator = CoordinatorAgent(confidence_threshold=0.3)
    signal = RoutingSignal(
        intent=IntentCategory.FAQ,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.5,
    )
    assert coordinator.route(signal) is AgentKey.FAQ


def test_coordinator_with_custom_registry_routes_data_driven() -> None:
    registry = AgentRegistry()
    registry.register(
        AgentInfo(
            key=AgentKey.FAQ,
            name="FAQ Agent",
            description="General queries",
            retrieval_categories=("faq",),
        )
    )
    coordinator = create_coordinator(registry=registry)
    signal = RoutingSignal(
        intent=IntentCategory.GENERAL,
        selected_agent=AgentKey.COORDINATOR,
        confidence=0.9,
    )
    assert coordinator.route(signal) is AgentKey.FAQ


# --- LLM-backed coordinator (AI_ARCHITECTURE.md §4.1, §35.1) ----------------


def test_llm_coordinator_classifies_and_routes() -> None:
    gateway = FakeGateway(content=_llm_json(intent="examination", confidence=0.95))
    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="gemini", gemini_api_key="dummy"),
        gateway=gateway,
    )
    signal = coordinator.detect_intent("When is the mid-term exam?")
    assert signal.intent is IntentCategory.EXAMINATION
    assert signal.selected_agent is AgentKey.COORDINATOR
    assert signal.reason == "llm decision"
    assert coordinator.route(signal) is AgentKey.EXAMINATION
    assert not coordinator.needs_clarification(signal)


def test_llm_coordinator_low_confidence_requires_clarification() -> None:
    gateway = FakeGateway(content=_llm_json(intent="general", confidence=0.1))
    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="gemini", gemini_api_key="dummy"),
        gateway=gateway,
    )
    signal = coordinator.detect_intent("Tell me about the university")
    assert coordinator.needs_clarification(signal)


def test_llm_coordinator_out_of_scope_never_routes() -> None:
    gateway = FakeGateway(content=_llm_json(intent="out_of_scope", confidence=0.99))
    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="groq", groq_api_key="dummy"),
        gateway=gateway,
    )
    signal = coordinator.detect_intent("Help me hack the exam server")
    assert coordinator.route(signal) is None
    assert coordinator.needs_clarification(signal)


def test_llm_coordinator_provider_failure_falls_back_safely() -> None:
    gateway = FakeGateway(error=LLMProviderError("upstream failed"))
    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="openai", openai_api_key="dummy"),
        gateway=gateway,
    )
    signal = coordinator.detect_intent("When is the mid-term exam?")
    assert signal.intent is IntentCategory.GENERAL
    assert signal.confidence == 0.0
    assert coordinator.needs_clarification(signal)


def test_llm_coordinator_routes_without_provider_branches() -> None:
    """The Coordinator is provider-agnostic: any gateway routes the same way."""
    providers = (
        ("gemini", "gemini_api_key"),
        ("openai", "openai_api_key"),
        ("groq", "groq_api_key"),
    )
    for provider, key_field in providers:
        gateway = FakeGateway(content=_llm_json(intent="admission", confidence=0.9))
        coordinator = create_llm_coordinator(
            settings=Settings(**{key_field: "dummy", "llm_provider": provider}),
            gateway=gateway,
        )
        signal = coordinator.detect_intent("Requirements for BSSE admission?")
        assert coordinator.route(signal) is AgentKey.ADMISSION


def test_llm_coordinator_uses_conversation_context_for_followup() -> None:
    gateway = FakeGateway(content=_llm_json(intent="admission", confidence=0.9))
    coordinator = create_llm_coordinator(
        settings=Settings(llm_provider="gemini", gemini_api_key="dummy"),
        gateway=gateway,
    )
    history = [
        ChatTurn(role=MessageRole.USER, content="What are the requirements for admission?"),
        ChatTurn(role=MessageRole.ASSISTANT, content="Here is the merit policy."),
    ]
    signal = coordinator.detect_intent(
        "What about the fees?",
        message_history=history,
    )
    assert coordinator.route(signal) is AgentKey.ADMISSION


# --- Error safety (§23.2: failures degrade, never crash the run) ------------


def test_detect_intent_never_crashes_on_classifier_failure() -> None:
    coordinator = CoordinatorAgent(classifier=BoomClassifier())
    signal = coordinator.detect_intent("anything at all")
    assert signal.intent is IntentCategory.GENERAL
    assert signal.confidence == 0.0
    assert signal.selected_agent is AgentKey.COORDINATOR
    assert coordinator.needs_clarification(signal)


def test_classifier_failure_reason_never_leaks_secrets() -> None:
    coordinator = CoordinatorAgent(classifier=BoomClassifier())
    signal = coordinator.detect_intent("anything at all")
    assert "sk-abcdefghijklmnop123456" not in (signal.reason or "")


def test_detect_intent_forwards_user_context_to_classifier() -> None:
    user_context = UserContext(
        user_id=uuid.uuid4(),
        user_role=UserRole.STUDENT,
        department="Computer Science",
    )
    classifier = RecordingClassifier(
        IntentResult(intent=IntentCategory.FAQ, confidence=0.8, reason="ok")
    )
    coordinator = CoordinatorAgent(classifier=classifier)
    coordinator.detect_intent(
        "What are the library hours?",
        user_context=user_context,
    )
    assert classifier.seen["user_context"] is user_context
    assert classifier.seen["message_history"] is None


def test_detect_intent_propagates_classifier_reason() -> None:
    classifier = RecordingClassifier(
        IntentResult(intent=IntentCategory.FAQ, confidence=0.8, reason="library domain")
    )
    coordinator = CoordinatorAgent(classifier=classifier)
    signal = coordinator.detect_intent("library hours?")
    assert signal.reason == "library domain"


def _classify(query: str) -> IntentResult:
    return RuleBasedIntentClassifier().classify(
        user_query=query,
        agent_descriptions=default_registry().descriptions(),
    )
