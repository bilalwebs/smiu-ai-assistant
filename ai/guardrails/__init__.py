"""AI guardrails and safety rules (AI_ARCHITECTURE.md §25-26).

The package owns the centralized safety boundary of the AI service: input
guardrails (prompt-injection, jailbreak, unsafe/restricted requests) and
output guardrails (unsafe output, leakage, authority claims) applied around
the specialist pipeline (AI_ARCHITECTURE.md §26.4).
"""

from __future__ import annotations

from ai.guardrails.guardrails import SafetyGuardrails, check_input, check_output, default_guardrails
from ai.guardrails.results import GuardrailCategory, GuardrailDecision

__all__ = [
    "GuardrailCategory",
    "GuardrailDecision",
    "SafetyGuardrails",
    "check_input",
    "check_output",
    "default_guardrails",
]
