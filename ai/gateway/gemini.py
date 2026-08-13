"""Gemini adapter for the LLM gateway (AI_ARCHITECTURE.md §35).

Wraps the ``google-genai`` SDK behind ``LLMGateway``. The SDK client is
injected at construction so tests run fully offline with a fake client; the
factory builds the real client from configuration.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from google.genai import types as genai_types

from ai.core.config import LLMProvider
from ai.gateway.base import (
    LLMGateway,
    LLMProviderError,
    LLMResponse,
    classify_error,
)


class GeminiGateway(LLMGateway):
    """Gateway adapter for Google Gemini via ``google-genai`` (§35.1)."""

    provider = LLMProvider.GEMINI

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
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if json_schema is not None else None,
            response_json_schema=json_schema if json_schema is not None else None,
        )
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=config,
            )
        # Provider exceptions are normalized via classify_error (incl. secrets).
        except Exception as exc:
            raise classify_error(exc, secrets=self._secrets) from exc

        if not response.candidates:
            raise LLMProviderError("Gemini returned no candidates")
        candidate = response.candidates[0]
        parts = candidate.content.parts if candidate.content is not None else ()
        content = "".join((part.text or "") for part in parts).strip()
        finish_reason = (
            candidate.finish_reason.value if candidate.finish_reason is not None else None
        )
        return LLMResponse(
            content=content,
            model=response.model_version,
            finish_reason=finish_reason,
        )
