"""Provider-agnostic LLM gateway (AI_ARCHITECTURE.md §35).

Purpose:
    A single abstraction between the AI service and every LLM provider. The
    Coordinator and the workflow consume ``LLMGateway.generate`` and never
    reference a provider SDK directly (§35.1). New providers are added by
    registering an adapter behind the gateway — no Coordinator, classifier, or
    workflow change (the §8 registration rules apply to the gateway too).

Layered failure handling (§23.1-23.3, §35.5-35.6):
    - transient failures (timeout, rate limit) are retried with bounded
      exponential backoff (max retries default 2),
    - when the primary model is exhausted, the gateway transparently retries
      the configured in-provider fallback model (§35.6),
    - non-transient failures surface as typed errors so callers degrade
      gracefully instead of crashing (§23.2).

Secrets:
    Provider SDK errors can echo configuration. Adapters redact the configured
    API key (and common key formats) before they build typed errors, so no
    credential ever reaches a reason string or a log.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from pydantic import BaseModel

from ai.core.config import LLMProvider

_REDACTED = "***REDACTED***"

# Common API-key formats (OpenAI sk-, Groq gsk_, Google AIza), Bearer tokens,
# and long high-entropy tokens.
_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{16,}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\b"),
)


def redact_secrets(text: str, secrets: Sequence[str] = ()) -> str:
    """Mask configured secrets and common API-key formats in ``text``."""
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, _REDACTED)
    for pattern in _KEY_PATTERNS:
        redacted = pattern.sub(_REDACTED, redacted)
    return redacted


class LLMResponse(BaseModel):
    """Typed completion returned by the gateway (§35.1).

    ``model`` records the id actually used (primary or fallback) for
    traceability (§35.7); ``finish_reason`` mirrors the provider's termination
    reason when available.
    """

    content: str
    model: str | None = None
    finish_reason: str | None = None


class LLMError(Exception):
    """Base class for typed gateway failures (§23)."""


class LLMConfigurationError(LLMError):
    """Misconfiguration: missing key, unknown provider, unsupported setup."""


class LLMTimeoutError(LLMError):
    """Transient: the provider call timed out (§23.1)."""


class LLMRateLimitError(LLMError):
    """Transient: provider rate limit or quota exceeded."""


class LLMProviderError(LLMError):
    """Non-transient provider-side failure (§23.2)."""


def classify_error(exc: Exception, *, secrets: Sequence[str] = ()) -> LLMError:
    """Map a raw provider/SDK exception to a typed ``LLMError``.

    Classification heuristics (status codes and message patterns) keep the
    mapping provider-agnostic; secrets are redacted from the surfaced message.
    """
    if isinstance(exc, LLMError):
        return exc
    message = redact_secrets(str(exc), secrets)
    lowered = message.lower()
    status = getattr(exc, "status_code", None)
    if status == 429 or "rate limit" in lowered or "quota" in lowered:
        return LLMRateLimitError(message)
    if status in (401, 403, 404):
        return LLMConfigurationError(message)
    if isinstance(exc, TimeoutError) or "timeout" in lowered or "timed out" in lowered:
        return LLMTimeoutError(message)
    return LLMProviderError(message)


class LLMGateway(ABC):
    """Provider-agnostic completion gateway (§35.1).

    Concrete adapters implement ``_complete`` (one raw, unretried provider
    call) and inherit the bounded backoff retry and in-provider model fallback.
    """

    provider: LLMProvider

    def __init__(
        self,
        *,
        model: str,
        fallback_model: str | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 30.0,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        backoff_base_seconds: float = 0.5,
        sleep_fn: Callable[[float], None] = time.sleep,
        secrets: Sequence[str] = (),
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
        self.backoff_base_seconds = backoff_base_seconds
        self._sleep_fn = sleep_fn
        self._secrets = tuple(secrets)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResponse:
        """Complete ``user_prompt`` with bounded retries and fallback (§35.5-35.6).

        Transient failures (timeout, rate limit) retry on the primary model
        with exponential backoff; when the primary is exhausted the configured
        in-provider fallback model is retried the same way. Non-transient
        failures propagate immediately as typed ``LLMError``.
        """
        resolved_temperature = self.default_temperature if temperature is None else temperature
        resolved_max_tokens = self.default_max_tokens if max_tokens is None else max_tokens
        try:
            return self._run_with_retries(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                json_schema=json_schema,
            )
        except (LLMTimeoutError, LLMRateLimitError) as primary_error:
            if self.fallback_model is None or self.fallback_model == self.model:
                raise primary_error
            return self._run_with_retries(
                model=self.fallback_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                json_schema=json_schema,
            )

    def _run_with_retries(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_schema: dict[str, object] | None,
    ) -> LLMResponse:
        last_error: LLMError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._complete(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_schema=json_schema,
                )
            except (LLMTimeoutError, LLMRateLimitError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    self._sleep_fn(self.backoff_base_seconds * (2**attempt))
        if last_error is not None:
            raise last_error
        raise LLMProviderError("LLM invocation failed without a classified error")

    @abstractmethod
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
        """One raw, unretried provider call (implemented by adapters)."""
        raise NotImplementedError
