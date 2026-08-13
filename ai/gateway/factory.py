"""Gateway factory: builds the configured ``LLMGateway`` (AI_ARCHITECTURE.md §35).

The factory is the only place that maps a provider to its SDK client and
adapter. It enforces the §35 rule that only the active provider's API key is
required — constructing a gateway with a missing key raises a clear
``LLMConfigurationError`` before any client is built. No network I/O happens at
construction time; SDK clients connect lazily on first request.
"""

from __future__ import annotations

import httpx
from google.genai import Client as GenaiClient
from google.genai import types as genai_types
from groq import Groq
from openai import OpenAI

from ai.core.config import LLMProvider, Settings
from ai.gateway.base import LLMConfigurationError, LLMGateway, redact_secrets
from ai.gateway.gemini import GeminiGateway
from ai.gateway.groq import GroqGateway
from ai.gateway.openai import OpenAIGateway


def build_llm_gateway(
    settings: Settings,
    provider: LLMProvider | None = None,
) -> LLMGateway:
    """Build the gateway for the active (or explicitly requested) provider.

    Raises:
        ``LLMConfigurationError`` when the provider is unsupported or its API
        key is not configured. The error message never contains the key.
    """
    resolved = provider if provider is not None else settings.llm_provider
    api_key = settings.api_key_for(resolved)
    if not api_key:
        raise LLMConfigurationError(
            f"no API key configured for LLM provider '{resolved.value}'"
        )
    # Any client-construction failure is surfaced as a configuration error with
    # the api key redacted from the message.
    try:
        client = _build_sdk_client(resolved, api_key, settings.llm_timeout_seconds)
    except Exception as exc:
        raise LLMConfigurationError(
            f"failed to initialize {resolved.value} client: "
            f"{redact_secrets(str(exc), (api_key,))}"
        ) from exc

    if resolved is LLMProvider.GEMINI:
        return GeminiGateway(
            client=client,
            model=settings.active_model(resolved),
            fallback_model=settings.llm_fallback_model or None,
            max_retries=settings.llm_max_retries,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=api_key,
        )
    if resolved is LLMProvider.OPENAI:
        return OpenAIGateway(
            client=client,
            model=settings.active_model(resolved),
            fallback_model=settings.llm_fallback_model or None,
            max_retries=settings.llm_max_retries,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=api_key,
        )
    return GroqGateway(
        client=client,
        model=settings.active_model(resolved),
        fallback_model=settings.llm_fallback_model or None,
        max_retries=settings.llm_max_retries,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=api_key,
    )


def _build_sdk_client(provider: LLMProvider, api_key: str, timeout_seconds: float) -> object:
    """Construct the provider SDK client without any network I/O.

    The ``httpx.Client`` is passed explicitly to the OpenAI/Groq clients to
    avoid the SDK default transport path, which is incompatible with the
    httpx version installed in this environment.
    """
    if provider is LLMProvider.GEMINI:
        return GenaiClient(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
    http_client = httpx.Client(timeout=timeout_seconds)
    if provider is LLMProvider.OPENAI:
        return OpenAI(api_key=api_key, http_client=http_client)
    return Groq(api_key=api_key, http_client=http_client)
