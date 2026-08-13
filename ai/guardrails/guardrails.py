"""Centralized AI safety/guardrail checks (AI_ARCHITECTURE.md §25-26).

Purpose:
    The single entry point for the AI service safety boundary:
      - ``check_input`` inspects a user query before specialist generation
        (§26.1 prompt-injection prevention, §26.2 jailbreak prevention, §26.3
        unsafe-prompt handling, §25 safety rules),
      - ``check_output`` scans a generated answer before delivery (§26.4
        output filtering, §37.4/§37.7 sensitive-data filtering).

    Both return a typed ``GuardrailDecision`` (allowed / category / internal
    reason / safe fallback). Blocked content never reaches the LLM (input) or
    the user (output), and internal detection details are never surfaced.

    RAG boundary: retrieved evidence is untrusted *data*. Guardrails do not
    scan evidence for instructions — the ContextBuilder already isolates
    evidence in a delimited, labeled block and the system prompt's grounding
    rules give it no instruction authority (§26.1, §34.5). The input check is
    applied to the user query at the pipeline boundary.
"""

from __future__ import annotations

from ai.guardrails.patterns import _INPUT_RULES, _OUTPUT_RULES
from ai.guardrails.results import GuardrailCategory, GuardrailDecision


class SafetyGuardrails:
    """Centralized input/output safety checks (AI_ARCHITECTURE.md §26)."""

    def check_input(self, text: str) -> GuardrailDecision:
        """Inspect a user query before generation (§26.1-26.3).

        Empty/whitespace input is classified as ``EMPTY`` but *allowed*: the
        pipeline handles it with the existing grounded no-answer path (§20.4)
        instead of a hard block, preserving degenerate-input behaviour.
        """
        if not text.strip():
            return GuardrailDecision(
                allowed=True,
                category=GuardrailCategory.EMPTY,
                reason="input.empty",
            )
        for rule in _INPUT_RULES:
            if rule.pattern.search(text):
                return GuardrailDecision(
                    allowed=False,
                    category=rule.category,
                    reason=rule.code,
                    fallback=rule.fallback,
                )
        return GuardrailDecision(
            allowed=True,
            category=GuardrailCategory.ALLOWED,
            reason="input.allowed",
        )

    def check_output(self, text: str) -> GuardrailDecision:
        """Scan a generated answer before delivery (§26.4, §37.7).

        Empty output is allowed so the existing unanswerable path (empty
        answer ⇒ no-answer response) is preserved.
        """
        if not text.strip():
            return GuardrailDecision(
                allowed=True,
                category=GuardrailCategory.ALLOWED,
                reason="output.empty_allowed",
            )
        for rule in _OUTPUT_RULES:
            if rule.pattern.search(text):
                return GuardrailDecision(
                    allowed=False,
                    category=rule.category,
                    reason=rule.code,
                    fallback=rule.fallback,
                )
        return GuardrailDecision(
            allowed=True,
            category=GuardrailCategory.ALLOWED,
            reason="output.allowed",
        )


_default_guardrails: SafetyGuardrails | None = None


def default_guardrails() -> SafetyGuardrails:
    """Return the cached, stateless default guardrail instance.

    Guardrails hold no mutable state, so a single shared instance is safe for
    every specialist agent (§3.5, §8 registration rules).
    """
    global _default_guardrails
    if _default_guardrails is None:
        _default_guardrails = SafetyGuardrails()
    return _default_guardrails


def check_input(text: str) -> GuardrailDecision:
    """Convenience input check on the default guardrails (§26)."""
    return default_guardrails().check_input(text)


def check_output(text: str) -> GuardrailDecision:
    """Convenience output check on the default guardrails (§26)."""
    return default_guardrails().check_output(text)
