"""OpenAI adapter for the LLM gateway (AI_ARCHITECTURE.md §35).

Wraps the ``openai`` SDK behind ``LLMGateway``. The SDK client is injected at
construction so tests run fully offline with a fake client; the factory builds
the real client from configuration.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ai.core.config import LLMProvider
from ai.gateway.base import (
    LLMGateway,
    LLMProviderError,
    LLMResponse,
    classify_error,
)


class OpenAIGateway(LLMGateway):
    """Gateway adapter for OpenAI chat completions (§35.1)."""

    provider = LLMProvider.OPENAI

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        fallback_model: str | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 30.0,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        backoff_base_seconds: float = 0.5,
        sleep_fn: Callable[[float], None] = time.sleep,
        api_key: str | None = None,
    ) -> None:
        super().__init__(
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
            backoff_base_seconds=backoff_base_seconds,
            sleep_fn=sleep_fn,
            secrets=(api_key,) if api_key else (),
        )
        self._client = client

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
        completion_kwargs: dict[str, object] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": self.timeout_seconds,
        }
        if json_schema is not None:
            completion_kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._client.chat.completions.create(**completion_kwargs)
        # Provider exceptions are normalized via classify_error (incl. secrets).
        except Exception as exc:
            raise classify_error(exc, secrets=self._secrets) from exc

        if not response.choices:
            raise LLMProviderError("OpenAI returned no choices")
        choice = response.choices[0]
        content = (choice.message.content or "") if choice.message is not None else ""
        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=choice.finish_reason,
        )
