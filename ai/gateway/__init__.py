"""Provider-agnostic LLM gateway package (AI_ARCHITECTURE.md §35).

Public surface: the ``LLMGateway`` abstraction, its typed errors, the
``build_llm_gateway`` factory, and the per-provider adapters. The Coordinator
and the workflow consume only ``LLMGateway`` — never a provider SDK.
"""

from ai.gateway.base import (
    LLMConfigurationError,
    LLMError,
    LLMGateway,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
    classify_error,
    redact_secrets,
)
from ai.gateway.factory import build_llm_gateway
from ai.gateway.gemini import GeminiGateway
from ai.gateway.groq import GroqGateway
from ai.gateway.openai import OpenAIGateway

__all__ = [
    "GeminiGateway",
    "GroqGateway",
    "LLMConfigurationError",
    "LLMError",
    "LLMGateway",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMResponse",
    "LLMTimeoutError",
    "OpenAIGateway",
    "build_llm_gateway",
    "classify_error",
    "redact_secrets",
]
