"""LLM-backed intent classifier tests (AI_ARCHITECTURE.md §9.1, §35).

All gateway calls are fakes injected at construction — the suite runs fully
offline with no API keys and no network. Coverage:
    - successful schema-constrained classification,
    - malformed / invalid output degrades to low-confidence GENERAL,
    - provider failure degrades safely with no credential leakage,
    - confidence clamping,
    - conversation history and user context are grounded into the prompt.
"""

from __future__ import annotations

import json
import uuid

from ai.agents.intent_classifier import LLMIntentClassifier
from ai.core.state import ChatTurn, IntentCategory, MessageRole, UserContext, UserRole
from ai.gateway.base import (
    LLMGateway,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
)


class FakeGateway(LLMGateway):
    """Scripted fake gateway recording every call (offline)."""

    def __init__(self, *, content: str = "", error: Exception | None = None) -> None:
        super().__init__(model="fake-model", max_retries=0)
        self.content = content
        self.error = error
        self.calls: list[dict[str, object]] = []

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
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
                "json_schema": json_schema,
            }
        )
        if self.error is not None:
            error = self.error
            self.error = None
            raise error
        return LLMResponse(content=self.content, model=model)


def _json_classification(
    *,
    intent: str = "admission",
    confidence: float = 0.9,
    secondary: list[str] | None = None,
    reason: str | None = "clear match",
) -> str:
    return json.dumps(
        {
            "intent": intent,
            "confidence": confidence,
            "secondary_intents": secondary or [],
            "reason": reason,
        }
    )


def test_classifies_admission_intent() -> None:
    gateway = FakeGateway(content=_json_classification())
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(
        user_query="What are the requirements for admission?",
        agent_descriptions="- admission: requirements and eligibility",
    )
    assert result.intent is IntentCategory.ADMISSION
    assert result.confidence == 0.9
    assert result.reason == "clear match"
    call = gateway.calls[0]
    assert call["json_schema"] is not None
    assert "requirements" in str(call["user_prompt"])
    assert "admission" in str(call["system_prompt"])


def test_parses_secondary_intents() -> None:
    gateway = FakeGateway(
        content=_json_classification(
            intent="examination",
            secondary=["admission"],
            reason="multi-topic",
        )
    )
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="admit card and fees?", agent_descriptions="d")
    assert result.intent is IntentCategory.EXAMINATION
    assert IntentCategory.ADMISSION in result.secondary_intents


def test_includes_history_and_user_context_in_prompt() -> None:
    gateway = FakeGateway(content=_json_classification())
    classifier = LLMIntentClassifier(gateway=gateway)
    history = [
        ChatTurn(role=MessageRole.USER, content="What are the requirements for admission?"),
        ChatTurn(role=MessageRole.ASSISTANT, content="Here is the merit policy."),
    ]
    user_context = UserContext(
        user_id=uuid.uuid4(),
        user_role=UserRole.STUDENT,
        department="Computer Science",
    )
    classifier.classify(
        user_query="What about the fees?",
        agent_descriptions="d",
        message_history=history,
        user_context=user_context,
    )
    prompt = str(gateway.calls[0]["user_prompt"])
    assert "What are the requirements for admission?" in prompt
    assert "Here is the merit policy." in prompt
    assert "role=student" in prompt
    assert "Computer Science" in prompt
    assert "What about the fees?" in prompt


def test_malformed_output_degrades_to_low_confidence_general() -> None:
    gateway = FakeGateway(content="this is not json")
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="hi", agent_descriptions="d")
    assert result.intent is IntentCategory.GENERAL
    assert result.confidence == 0.0
    assert "malformed" in (result.reason or "")


def test_invalid_intent_value_degrades_safely() -> None:
    gateway = FakeGateway(content=_json_classification(intent="not-a-real-intent", confidence=0.99))
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="hi", agent_descriptions="d")
    assert result.intent is IntentCategory.GENERAL
    assert result.confidence == 0.0


def test_invalid_secondary_intents_are_skipped() -> None:
    gateway = FakeGateway(
        content=_json_classification(intent="faq", secondary=["admission", "bogus"])
    )
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="library hours", agent_descriptions="d")
    assert result.intent is IntentCategory.FAQ
    assert result.secondary_intents == [IntentCategory.ADMISSION]


def test_confidence_is_clamped() -> None:
    for raw, expected in ((1.5, 1.0), (-0.5, 0.0), (0.7, 0.7)):
        gateway = FakeGateway(content=_json_classification(confidence=raw))
        classifier = LLMIntentClassifier(gateway=gateway)
        result = classifier.classify(user_query="hi", agent_descriptions="d")
        assert result.confidence == expected


def test_provider_failure_degrades_to_low_confidence_general() -> None:
    gateway = FakeGateway(error=LLMRateLimitError("rate limit exceeded"))
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="admission?", agent_descriptions="d")
    assert result.intent is IntentCategory.GENERAL
    assert result.confidence == 0.0
    assert (result.reason or "").startswith("LLM classification unavailable")


def test_provider_failure_never_leaks_secrets() -> None:
    secret = "sk-leak-me-abcdefghijklmnopq"
    gateway = FakeGateway(error=LLMProviderError(f"key {secret} rejected"))
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="admission?", agent_descriptions="d")
    assert secret not in (result.reason or "")


def test_low_confidence_llm_result_is_never_inflated() -> None:
    gateway = FakeGateway(content=_json_classification(intent="general", confidence=0.05))
    classifier = LLMIntentClassifier(gateway=gateway)
    result = classifier.classify(user_query="tell me about the university", agent_descriptions="d")
    assert result.confidence <= 0.05
