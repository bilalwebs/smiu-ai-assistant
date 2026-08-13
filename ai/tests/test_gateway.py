"""LLM gateway tests (AI_ARCHITECTURE.md §23, §35).

All provider SDK calls are fakes injected at construction — the suite runs
fully offline with no API keys and no network. Coverage:
    - provider selection and model resolution via the factory,
    - missing-key handling (fail fast, no credential leakage),
    - bounded backoff retry for transient failures (timeout/rate limit),
    - in-provider fallback model after primary exhaustion (§35.6),
    - immediate propagation of non-transient failures,
    - secret redaction in errors,
    - response parsing for the Gemini, OpenAI, and Groq adapters.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai.core.config import LLMProvider, Settings
from ai.gateway.base import (
    LLMConfigurationError,
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


def make_settings(**overrides: object) -> Settings:
    """Deterministic settings: init kwargs beat any developer env vars."""
    base: dict[str, object] = {
        "llm_provider": LLMProvider.GEMINI,
        "gemini_api_key": "AIza-test-key-0000",
        "llm_model": "",
        "llm_fallback_model": None,
    }
    base.update(overrides)
    return Settings(**base)


class ScriptedGateway(LLMGateway):
    """Fake gateway whose ``_complete`` outcome is scripted per model."""

    def __init__(
        self,
        *,
        outcomes: dict[str, list[object]],
        fallback_model: str | None = "fallback",
        max_retries: int = 2,
    ) -> None:
        super().__init__(
            model="primary",
            fallback_model=fallback_model,
            max_retries=max_retries,
            sleep_fn=self._record_sleep,
        )
        self.outcomes: dict[str, list[object]] = {
            model: list(items) for model, items in outcomes.items()
        }
        self.calls: list[str] = []
        self.sleeps: list[float] = []

    def _record_sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

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
        self.calls.append(model)
        queue = self.outcomes.setdefault(model, [])
        if len(queue) == 1 and isinstance(queue[0], BaseException):
            raise queue[0]
        if queue:
            outcome = queue.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            if isinstance(outcome, LLMResponse):
                return outcome
        return LLMResponse(content=f"{model}-default", model=model)


# --- Secret redaction (no credential leakage) -------------------------------


def test_redact_secrets_masks_configured_value() -> None:
    secret = "sk-super-secret-value-abcdefghij"
    redacted = redact_secrets(f"auth failed for {secret}", secrets=[secret])
    assert secret not in redacted
    assert "***REDACTED***" in redacted


def test_redact_secrets_masks_common_key_formats() -> None:
    assert "sk-abcdefghijklmnop123456" not in redact_secrets("bad key sk-abcdefghijklmnop123456")
    assert "gsk_abcdefghijklmnop123456" not in redact_secrets("bad gsk_abcdefghijklmnop123456")
    assert "AIzaSyabcdefghijklmnop123456" not in redact_secrets("bad AIzaSyabcdefghijklmnop123456")
    assert "bearer abcdefghijklmnopqrstuvwxyz0123" not in redact_secrets(
        "authorization bearer abcdefghijklmnopqrstuvwxyz0123"
    )


# --- Error classification ---------------------------------------------------


def test_classify_error_maps_status_codes() -> None:
    def _exc(status: int | None) -> Exception:
        error = Exception("provider said no")
        error.status_code = status
        return error

    assert isinstance(classify_error(_exc(429)), LLMRateLimitError)
    assert isinstance(classify_error(_exc(401)), LLMConfigurationError)
    assert isinstance(classify_error(_exc(403)), LLMConfigurationError)
    assert isinstance(classify_error(_exc(404)), LLMConfigurationError)
    assert isinstance(classify_error(_exc(500)), LLMProviderError)


def test_classify_error_maps_timeout_and_rate_limit_by_message() -> None:
    assert isinstance(classify_error(TimeoutError("request timed out")), LLMTimeoutError)
    assert isinstance(classify_error(Exception("rate limit exceeded")), LLMRateLimitError)
    assert isinstance(classify_error(Exception("quota exceeded")), LLMRateLimitError)


def test_classify_error_redacts_secrets_from_message() -> None:
    secret = "sk-top-secret-abcdefghijklmnopq"
    error = classify_error(Exception(f"authentication failed: {secret}"), secrets=[secret])
    assert secret not in str(error)


def test_classify_error_passes_typed_errors_through() -> None:
    typed = LLMProviderError("already typed")
    assert classify_error(typed) is typed


# --- Factory: provider selection and model resolution -----------------------


def test_factory_selects_gemini() -> None:
    gateway = build_llm_gateway(make_settings(llm_provider=LLMProvider.GEMINI))
    assert isinstance(gateway, GeminiGateway)
    assert gateway.provider is LLMProvider.GEMINI
    assert gateway.model == "gemini-2.5-flash"


def test_factory_selects_openai() -> None:
    gateway = build_llm_gateway(
        make_settings(llm_provider=LLMProvider.OPENAI, openai_api_key="sk-test-key-1234")
    )
    assert isinstance(gateway, OpenAIGateway)
    assert gateway.provider is LLMProvider.OPENAI
    assert gateway.model == "gpt-4o-mini"


def test_factory_selects_groq() -> None:
    gateway = build_llm_gateway(
        make_settings(llm_provider=LLMProvider.GROQ, groq_api_key="gsk-test-key-1234")
    )
    assert isinstance(gateway, GroqGateway)
    assert gateway.provider is LLMProvider.GROQ
    assert gateway.model == "llama-3.1-8b-instant"


def test_factory_applies_generic_model_override_to_any_provider() -> None:
    gateway = build_llm_gateway(
        make_settings(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="sk-test-key-1234",
            llm_model="custom-model",
        )
    )
    assert gateway.model == "custom-model"


def test_factory_applies_fallback_model() -> None:
    gateway = build_llm_gateway(
        make_settings(llm_fallback_model="fallback-model")
    )
    assert gateway.fallback_model == "fallback-model"


def test_factory_missing_key_raises_configuration_error() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        openai_api_key="",
        llm_model="",
        llm_fallback_model=None,
    )
    with pytest.raises(LLMConfigurationError) as excinfo:
        build_llm_gateway(settings)
    assert "openai" in str(excinfo.value)


def test_factory_missing_key_error_never_leaks_secrets() -> None:
    settings = Settings(llm_provider=LLMProvider.GROQ, groq_api_key="", llm_model="")
    with pytest.raises(LLMConfigurationError) as excinfo:
        build_llm_gateway(settings)
    assert "gsk_" not in str(excinfo.value)
    assert "API key" in str(excinfo.value)


# --- Retry + fallback behavior (base gateway) -------------------------------


def test_first_attempt_success_no_retry_no_backoff() -> None:
    gateway = ScriptedGateway(outcomes={"primary": [LLMResponse(content="ok")]})
    response = gateway.generate(system_prompt="s", user_prompt="u")
    assert response.content == "ok"
    assert gateway.calls == ["primary"]
    assert gateway.sleeps == []


def test_transient_failure_is_retried_with_backoff() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMTimeoutError("t"), LLMResponse(content="ok")]}
    )
    response = gateway.generate(system_prompt="s", user_prompt="u")
    assert response.content == "ok"
    assert gateway.calls == ["primary", "primary"]
    assert gateway.sleeps == [0.5]


def test_backoff_exponential_across_retries() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMTimeoutError("t")]},
        fallback_model=None,
        max_retries=2,
    )
    with pytest.raises(LLMTimeoutError):
        gateway.generate(system_prompt="s", user_prompt="u")
    assert gateway.calls == ["primary", "primary", "primary"]
    assert gateway.sleeps == [0.5, 1.0]


def test_non_transient_failure_is_not_retried() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMProviderError("bad request")]},
        max_retries=2,
    )
    with pytest.raises(LLMProviderError):
        gateway.generate(system_prompt="s", user_prompt="u")
    assert gateway.calls == ["primary"]
    assert gateway.sleeps == []


def test_fallback_model_used_after_primary_exhaustion() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMTimeoutError("t")]},
        max_retries=2,
    )
    response = gateway.generate(system_prompt="s", user_prompt="u")
    assert response.content == "fallback-default"
    assert gateway.calls == ["primary", "primary", "primary", "fallback"]


def test_no_fallback_raises_after_primary_exhaustion() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMTimeoutError("t")]},
        fallback_model=None,
        max_retries=2,
    )
    with pytest.raises(LLMTimeoutError):
        gateway.generate(system_prompt="s", user_prompt="u")
    assert gateway.calls == ["primary", "primary", "primary"]


def test_fallback_also_failing_raises() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMTimeoutError("t")], "fallback": [LLMTimeoutError("t")]},
        max_retries=2,
    )
    with pytest.raises(LLMTimeoutError):
        gateway.generate(system_prompt="s", user_prompt="u")
    assert gateway.calls == ["primary", "primary", "primary", "fallback", "fallback", "fallback"]


def test_rate_limit_is_retried_like_timeout() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMRateLimitError("429"), LLMResponse(content="ok")]}
    )
    response = gateway.generate(system_prompt="s", user_prompt="u")
    assert response.content == "ok"
    assert gateway.sleeps == [0.5]


def test_rate_limit_after_primary_triggers_fallback() -> None:
    gateway = ScriptedGateway(
        outcomes={"primary": [LLMRateLimitError("429")]},
        max_retries=2,
    )
    response = gateway.generate(system_prompt="s", user_prompt="u")
    assert response.content == "fallback-default"


# --- OpenAI adapter ---------------------------------------------------------


class _FakeCompletions:
    def __init__(self, response: object, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


def _openai_client(
    *, content: str | None = "hi", error: Exception | None = None
) -> tuple[object, _FakeCompletions]:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    response = SimpleNamespace(choices=[choice], model="gpt-4o-mini")
    completions = _FakeCompletions(response, error)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_openai_adapter_parses_response() -> None:
    client, completions = _openai_client()
    gateway = OpenAIGateway(client=client, model="gpt-4o-mini", api_key="sk-test-key-1234")
    response = gateway.generate(system_prompt="sys", user_prompt="usr")
    assert response.content == "hi"
    assert response.model == "gpt-4o-mini"
    assert response.finish_reason == "stop"
    assert completions.kwargs["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert completions.kwargs["timeout"] == gateway.timeout_seconds
    assert "response_format" not in completions.kwargs


def test_openai_adapter_forwards_json_schema() -> None:
    client, completions = _openai_client()
    gateway = OpenAIGateway(client=client, model="gpt-4o-mini")
    gateway.generate(system_prompt="s", user_prompt="u", json_schema={"type": "object"})
    assert completions.kwargs["response_format"] == {"type": "json_object"}


def test_openai_adapter_maps_rate_limit_error() -> None:
    error = Exception("rate limit exceeded")
    error.status_code = 429
    client, _ = _openai_client(error=error)
    gateway = OpenAIGateway(client=client, model="gpt-4o-mini", max_retries=0)
    with pytest.raises(LLMRateLimitError):
        gateway.generate(system_prompt="s", user_prompt="u")


def test_openai_adapter_redacts_key_from_error() -> None:
    secret = "sk-secret-value-abcdefghijklmnop"
    error = Exception(f"invalid api key {secret}")
    error.status_code = 401
    client, _ = _openai_client(error=error)
    gateway = OpenAIGateway(client=client, model="gpt-4o-mini", api_key=secret, max_retries=0)
    with pytest.raises(LLMConfigurationError) as excinfo:
        gateway.generate(system_prompt="s", user_prompt="u")
    assert secret not in str(excinfo.value)


def test_openai_adapter_empty_choices_raises_provider_error() -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=_FakeCompletions(SimpleNamespace(choices=[], model="gpt-4o-mini"))
        )
    )
    gateway = OpenAIGateway(client=client, model="gpt-4o-mini", max_retries=0)
    with pytest.raises(LLMProviderError):
        gateway.generate(system_prompt="s", user_prompt="u")


# --- Groq adapter -----------------------------------------------------------


def test_groq_adapter_parses_response() -> None:
    message = SimpleNamespace(content="hi", role="assistant")
    choice = SimpleNamespace(message=message, finish_reason="stop")
    response = SimpleNamespace(choices=[choice], model="llama-3.1-8b-instant")
    completions = _FakeCompletions(response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    gateway = GroqGateway(client=client, model="llama-3.1-8b-instant")
    result = gateway.generate(system_prompt="sys", user_prompt="usr")
    assert result.content == "hi"
    assert result.model == "llama-3.1-8b-instant"
    assert completions.kwargs["messages"][0] == {"role": "system", "content": "sys"}


def test_groq_adapter_maps_timeout_error() -> None:
    completions = _FakeCompletions(None, error=TimeoutError("timed out"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    gateway = GroqGateway(client=client, model="llama-3.1-8b-instant", max_retries=0)
    with pytest.raises(LLMTimeoutError):
        gateway.generate(system_prompt="s", user_prompt="u")


# --- Gemini adapter ---------------------------------------------------------


def _gemini_client(
    response: object, error: Exception | None = None
) -> tuple[object, dict[str, object]]:
    calls: dict[str, object] = {}

    def generate_content(*, model: str, contents: object, config: object) -> object:
        calls["model"] = model
        calls["contents"] = contents
        calls["config"] = config
        if error is not None:
            raise error
        return response

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return client, calls


def _gemini_response(text: str) -> object:
    from google.genai import types as genai_types

    return genai_types.GenerateContentResponse.model_validate(
        {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finish_reason": "STOP",
                }
            ],
            "model_version": "gemini-2.5-flash",
        }
    )


def test_gemini_adapter_parses_response() -> None:
    client, calls = _gemini_client(_gemini_response("hello"))
    gateway = GeminiGateway(client=client, model="gemini-2.5-flash")
    response = gateway.generate(system_prompt="sys", user_prompt="usr")
    assert response.content == "hello"
    assert response.model == "gemini-2.5-flash"
    assert response.finish_reason == "STOP"
    assert calls["contents"] == "usr"


def test_gemini_adapter_forwards_json_schema() -> None:
    client, calls = _gemini_client(_gemini_response("{}"))
    gateway = GeminiGateway(client=client, model="gemini-2.5-flash")
    gateway.generate(system_prompt="s", user_prompt="u", json_schema={"type": "object"})
    config = calls["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == {"type": "object"}


def test_gemini_adapter_no_schema_keeps_text_output() -> None:
    client, calls = _gemini_client(_gemini_response("plain"))
    gateway = GeminiGateway(client=client, model="gemini-2.5-flash")
    gateway.generate(system_prompt="s", user_prompt="u")
    assert calls["config"].response_mime_type is None


def test_gemini_adapter_maps_timeout_error() -> None:
    client, _ = _gemini_client(_gemini_response("x"), error=TimeoutError("timed out"))
    gateway = GeminiGateway(client=client, model="gemini-2.5-flash", max_retries=0)
    with pytest.raises(LLMTimeoutError):
        gateway.generate(system_prompt="s", user_prompt="u")


def test_gemini_adapter_empty_candidates_raises_provider_error() -> None:
    from google.genai import types as genai_types

    response = genai_types.GenerateContentResponse.model_validate({"candidates": []})
    client, _ = _gemini_client(response)
    gateway = GeminiGateway(client=client, model="gemini-2.5-flash", max_retries=0)
    with pytest.raises(LLMProviderError):
        gateway.generate(system_prompt="s", user_prompt="u")
