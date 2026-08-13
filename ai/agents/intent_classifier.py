"""Intent classification for the Coordinator (AI_ARCHITECTURE.md §9.1).

Purpose:
    The Coordinator classifies the current query (plus conversation context)
    into a typed ``IntentResult``: intent label, confidence, secondary intents.
    Classification is structured, never free-form text (§4.3), and is grounded
    in the Agent Manager registry descriptions (§9.1).

    The classifier is defined behind the ``IntentClassifier`` protocol so the
    real LLM-backed classifier (``LLMIntentClassifier``) can sit behind the
    model gateway (§35) without touching the Coordinator.
    ``RuleBasedIntentClassifier`` is a deterministic implementation used for
    automated suites (mocked LLM, TESTING_STRATEGY.md §23.2) and local
    development before a gateway is configured.

    Safety precedence (§9.3, §25-26): a detected safety/restricted-topic signal
    (cheating, personal data of others, medical/legal/financial advice) always
    wins over any domain match.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field

from ai.core.state import ChatTurn, IntentCategory, UserContext
from ai.gateway.base import LLMError, LLMGateway, redact_secrets


class IntentResult(BaseModel):
    """Typed classification output (AI_ARCHITECTURE.md §9.1)."""

    intent: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    secondary_intents: list[IntentCategory] = Field(default_factory=list)
    reason: str | None = None


class IntentClassifier(Protocol):
    """Classifies a user query into a typed intent (AI_ARCHITECTURE.md §9.1)."""

    def classify(
        self,
        *,
        user_query: str,
        agent_descriptions: str,
        message_history: Sequence[ChatTurn] | None = None,
        user_context: UserContext | None = None,
    ) -> IntentResult:
        """Return the typed intent classification for ``user_query``."""
        ...


def _word_match(phrase: str, text: str) -> bool:
    """Word-boundary match; a trailing ``*`` matches the stem as a prefix."""
    if phrase.endswith("*"):
        pattern = rf"\b{re.escape(phrase[:-1])}\w*"
    else:
        pattern = rf"\b{re.escape(phrase)}\b"
    return re.search(pattern, text) is not None


# Restricted/safety topics (§25.1-25.2, §26.3). A single hit forces the
# out-of-scope intent ahead of any domain keyword (§9.3 action-safety precedence).
_SAFETY_PHRASES: tuple[str, ...] = (
    "hack",
    "cheat",
    "cheating",
    "bribe",
    "leak",
    "forged",
    "fake documents",
    "someone else's",
    "another student's",
    "other student's",
    "medical advice",
    "legal advice",
    "financial advice",
    "tax advice",
    "loan",
    "drug",
    "weapon",
    "harass",
)

# Domain keywords with weights; a higher weight marks a strong, domain-specific
# signal (e.g. "admit card" almost always means the Examination domain).
_DOMAIN_KEYWORDS: dict[IntentCategory, dict[str, int]] = {
    IntentCategory.EXAMINATION: {
        "exam*": 2,
        "date sheet": 2,
        "datesheet": 2,
        "admit card": 2,
        "result": 2,
        "mid-term": 2,
        "midterm": 2,
        "improvement": 1,
        "supply": 1,
        "recheck": 1,
        "paper": 1,
        "transcript": 1,
        "mark sheet": 1,
        "marksheet": 1,
        "grading": 1,
        "practical": 1,
        "viva": 1,
    },
    IntentCategory.ADMISSION: {
        "admission": 2,
        "merit": 2,
        "bsse": 2,
        "bscs": 2,
        "apply": 1,
        "application": 1,
        "eligib*": 1,
        "documents": 1,
        "requirements": 1,
        "intake": 1,
        "program": 1,
        "enrol*": 1,
        "fee": 1,
        "fees": 1,
        "scholarship": 1,
        "prospectus": 1,
    },
    IntentCategory.FAQ: {
        "library": 2,
        "office": 1,
        "timing": 1,
        "timings": 1,
        "hours": 1,
        "contact": 1,
        "campus": 1,
        "hostel": 1,
        "transport": 1,
        "department": 1,
        "phone": 1,
        "email": 1,
        "address": 1,
        "location": 1,
        "registrar": 1,
        "where": 1,
        "faculty": 1,
    },
}

_HISTORY_CONTEXT_TURNS = 2


class RuleBasedIntentClassifier:
    """Deterministic keyword classifier: the dev/test stand-in for the LLM.

    The classifier is a pure function of its inputs — identical queries produce
    identical results, which is what automated suites require (mocked LLM,
    TESTING_STRATEGY.md §23.2). It also implements the §4.3 requirement that
    intent analysis use conversation context: keywords from the most recent
    history turns contribute (at lower weight) so follow-ups route correctly.
    ``user_context`` is accepted for interface parity with the LLM classifier
    but does not affect the deterministic keyword scoring.
    """

    def classify(
        self,
        *,
        user_query: str,
        agent_descriptions: str,
        message_history: Sequence[ChatTurn] | None = None,
        user_context: UserContext | None = None,
    ) -> IntentResult:
        query_text = user_query.lower()
        history_text = " ".join(
            turn.content for turn in (message_history or ())[-_HISTORY_CONTEXT_TURNS:]
        ).lower()

        for phrase in _SAFETY_PHRASES:
            if _word_match(phrase, query_text):
                return IntentResult(
                    intent=IntentCategory.OUT_OF_SCOPE,
                    confidence=0.95,
                    reason=f"safety-restricted topic detected: '{phrase}'",
                )

        scores: dict[IntentCategory, int] = {}
        for category, table in _DOMAIN_KEYWORDS.items():
            total = 0
            for phrase, weight in table.items():
                if _word_match(phrase, query_text):
                    total += weight * 2
                elif history_text and _word_match(phrase, history_text):
                    total += weight
            if total > 0:
                scores[category] = total

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ranked:
            return IntentResult(
                intent=IntentCategory.GENERAL,
                confidence=0.2,
                reason="no domain keyword matched; treated as unknown",
            )

        best, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        confidence = best_score / (best_score + second_score + 1.0)
        secondary = [cat for cat, score in scores.items() if score > 0 and cat is not best]
        return IntentResult(
            intent=best,
            confidence=round(confidence, 4),
            secondary_intents=secondary,
            reason=f"keyword score {best_score} vs runner-up {second_score}",
        )


# --- LLM-backed classification (AI_ARCHITECTURE.md §35.1, §9.1) -------------

_CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [intent.value for intent in IntentCategory],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "secondary_intents": {
            "type": "array",
            "items": {"type": "string", "enum": [intent.value for intent in IntentCategory]},
        },
        "reason": {"type": "string"},
    },
    "required": ["intent", "confidence", "secondary_intents"],
}

_SYSTEM_CLASSIFICATION_PROMPT = (
    "You are the intent classifier of a university assistant. Classify the "
    "user's latest message into exactly one of these intents: "
    f"{', '.join(intent.value for intent in IntentCategory)}. "
    "Use the agent capability descriptions as grounding. The 'general' intent "
    "is for unspecific or ambiguous messages; 'out_of_scope' is for requests "
    "outside the assistant's role (including safety-restricted topics such as "
    "cheating, hacking, or personal data of others). Assign a low confidence "
    "when the message is ambiguous or does not clearly match a domain. "
    'Respond with JSON only, following the schema: {"intent": "...", '
    '"confidence": 0.0, "secondary_intents": [], "reason": "..."}'
)


def _safe_fallback(reason: str) -> IntentResult:
    """Low-confidence GENERAL result used when the LLM path cannot classify.

    The confidence stays at the floor (never inflated) so the router treats the
    turn as ambiguous and returns a clarifying turn (§9.4, §28).
    """
    return IntentResult(
        intent=IntentCategory.GENERAL,
        confidence=0.0,
        reason=reason,
    )


def _parse_intent_json(content: str) -> IntentResult:
    """Parse the strict-JSON classification output; malformed output degrades safely."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return _safe_fallback("LLM classification output was malformed")
    if not isinstance(data, dict):
        return _safe_fallback("LLM classification output was not a JSON object")

    try:
        intent = IntentCategory(data["intent"])
    except (KeyError, TypeError, ValueError):
        return _safe_fallback("LLM classification output had an invalid intent")

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        return _safe_fallback("LLM classification output had an invalid confidence")
    confidence = min(max(confidence, 0.0), 1.0)

    secondary_intents: list[IntentCategory] = []
    raw_secondary = data.get("secondary_intents", [])
    if isinstance(raw_secondary, list):
        for value in raw_secondary:
            try:
                secondary_intents.append(IntentCategory(value))
            except (TypeError, ValueError):
                continue

    raw_reason = data.get("reason")
    reason = str(raw_reason).strip() if raw_reason is not None else None
    return IntentResult(
        intent=intent,
        confidence=confidence,
        secondary_intents=secondary_intents,
        reason=reason,
    )


class LLMIntentClassifier:
    """LLM-backed intent classifier behind the model gateway (§35.1, §9.1).

    Provider-agnostic: it consumes only ``LLMGateway`` and never references an
    SDK. Classification is schema-constrained JSON (§35 structured output) at
    the factuality-first temperature; provider failures and malformed output
    degrade to a low-confidence GENERAL result with a safe reason instead of
    raising into the Coordinator.
    """

    def __init__(
        self,
        *,
        gateway: LLMGateway,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._gateway = gateway
        self._temperature = temperature
        self._max_tokens = max_tokens

    def classify(
        self,
        *,
        user_query: str,
        agent_descriptions: str,
        message_history: Sequence[ChatTurn] | None = None,
        user_context: UserContext | None = None,
    ) -> IntentResult:
        user_prompt = _build_classification_prompt(
            user_query=user_query,
            agent_descriptions=agent_descriptions,
            message_history=message_history,
            user_context=user_context,
        )
        try:
            response = self._gateway.generate(
                system_prompt=_SYSTEM_CLASSIFICATION_PROMPT,
                user_prompt=user_prompt,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                json_schema=_CLASSIFICATION_SCHEMA,
            )
        except LLMError as exc:
            return _safe_fallback(
                f"LLM classification unavailable: {redact_secrets(str(exc))}"
            )
        return _parse_intent_json(response.content)


def _build_classification_prompt(
    *,
    user_query: str,
    agent_descriptions: str,
    message_history: Sequence[ChatTurn] | None,
    user_context: UserContext | None,
) -> str:
    """Assemble the classification prompt (§9.1 grounding, §9.3 continuity)."""
    sections = [
        f"Agent capabilities:\n{agent_descriptions}",
        "Conversation history (recent turns first):",
    ]
    history = list(message_history or ())
    if history:
        sections.append("\n".join(f"- {turn.role.value}: {turn.content}" for turn in history[-8:]))
    else:
        sections.append("- (none)")
    if user_context is not None:
        sections.append(
            "User context: "
            f"role={user_context.user_role.value}, "
            f"department={user_context.department or 'unknown'}"
        )
    sections.append(f"Latest user message:\n{user_query}")
    return "\n\n".join(sections)
