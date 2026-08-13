"""Typed guardrail results (AI_ARCHITECTURE.md §26.4-26.5).

Purpose:
    Guardrail checks return a typed decision rather than a bare boolean so the
    specialist pipeline can distinguish *why* content was handled and which
    safe fallback to surface. Internal detection details (``reason``) are
    never exposed to users — only the category's safe ``fallback`` text is
    (AI_ARCHITECTURE.md §26.3, §37).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class GuardrailCategory(StrEnum):
    """Guardrail classifications (AI_ARCHITECTURE.md §25-26).

    ``ALLOWED`` marks a pass; every other value names the safety policy a
    check flagged. ``EMPTY`` is informational, not a block: degenerate input
    is handled by the existing grounded no-answer path (§20.4, §28.3) rather
    than hard-blocked, so normal empty-trim behaviour is preserved.
    """

    ALLOWED = "allowed"
    EMPTY = "empty"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SYSTEM_PROMPT_REQUEST = "system_prompt_request"
    CHEATING = "cheating"
    HATE_HARASSMENT = "hate_harassment"
    PRIVATE_DATA = "private_data"
    RESTRICTED_TOPIC = "restricted_topic"
    OUT_OF_SCOPE = "out_of_scope"
    UNSAFE_OUTPUT = "unsafe_output"
    AUTHORITY_CLAIM = "authority_claim"
    SENSITIVE_DATA = "sensitive_data"


class GuardrailDecision(BaseModel):
    """Result of a guardrail check (§26.4, §26.5).

    ``allowed`` is True only for content that passes. ``reason`` is a stable
    machine code used for internal reporting (never user-facing — internal
    detection details are not exposed to users, §26.3/§37). ``fallback`` is
    the safe user-facing response to use when the content is blocked.
    """

    allowed: bool
    category: GuardrailCategory
    reason: str
    fallback: str | None = None
