"""AI configuration tests (AI_ARCHITECTURE.md §2.2, §35).

Verify that configuration:
    - constructs without external services or network access,
    - honors environment variables,
    - validates required values (fail fast on malformed input).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai.core.config import (
    Environment,
    LLMProvider,
    ProductionSettings,
    Settings,
    TestingSettings,
    clear_settings_cache,
    get_settings,
)


def test_default_settings_construct_without_external_services() -> None:
    settings = Settings()
    assert settings.environment is Environment.DEVELOPMENT
    assert settings.llm_provider is LLMProvider.GEMINI
    assert settings.llm_model == ""
    assert settings.active_model() == "gemini-2.5-flash"
    assert settings.llm_temperature == 0.1
    assert settings.llm_max_retries == 2
    assert settings.rag_top_k == 4
    assert settings.chat_history_limit == 20
    assert settings.vector_store_path == "knowledge/vectorstore"


def test_active_model_uses_provider_defaults() -> None:
    settings = Settings(llm_provider=LLMProvider.GEMINI, llm_model="")
    assert settings.active_model() == "gemini-2.5-flash"
    assert settings.active_model(LLMProvider.GEMINI) == "gemini-2.5-flash"
    assert settings.active_model(LLMProvider.OPENAI) == "gpt-4o-mini"
    assert settings.active_model(LLMProvider.GROQ) == "llama-3.1-8b-instant"


def test_active_model_generic_override_wins_for_any_provider() -> None:
    settings = Settings(llm_model="custom-model", llm_provider=LLMProvider.GROQ)
    assert settings.active_model() == "custom-model"
    assert settings.active_model(LLMProvider.OPENAI) == "custom-model"


def test_api_key_for_returns_configured_key() -> None:
    settings = Settings(
        gemini_api_key="k-gemini",
        openai_api_key="k-openai",
        groq_api_key="k-groq",
    )
    assert settings.api_key_for(LLMProvider.GEMINI) == "k-gemini"
    assert settings.api_key_for(LLMProvider.OPENAI) == "k-openai"
    assert settings.api_key_for(LLMProvider.GROQ) == "k-groq"
    assert settings.api_key_for() == "k-gemini"


def test_llm_provider_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    settings = Settings(llm_model="")
    assert settings.llm_provider is LLMProvider.GROQ
    assert settings.active_model() == "llama-3.1-8b-instant"


def test_provider_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    settings = Settings(llm_provider=LLMProvider.GROQ, llm_model="")
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert settings.active_model() == "llama-3.3-70b-versatile"


def test_testing_settings_are_isolated_from_env_file() -> None:
    settings = TestingSettings()
    assert settings.environment is Environment.TESTING
    assert settings.debug is True
    assert settings.log_level == "DEBUG"


def test_get_settings_returns_cached_instance_and_clears() -> None:
    clear_settings_cache()
    first = get_settings()
    second = get_settings()
    assert first is second
    clear_settings_cache()
    third = get_settings()
    assert third is not first


def test_environment_variable_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.0")
    monkeypatch.setenv("RAG_TOP_K", "6")
    settings = Settings()
    assert settings.llm_model == "custom-model"
    assert settings.llm_temperature == 0.0
    assert settings.rag_top_k == 6


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="TRACE")


def test_temperature_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_temperature=1.5)
    with pytest.raises(ValidationError):
        Settings(llm_temperature=-0.1)
    assert Settings(llm_temperature=0.0).llm_temperature == 0.0


def test_rag_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(rag_top_k=0)


def test_production_requires_connection_critical_values() -> None:
    with pytest.raises(ValidationError):
        ProductionSettings()
    with pytest.raises(ValidationError):
        ProductionSettings(embedding_model="")
    settings = ProductionSettings(
        embedding_model="sentence-transformers/example-model",
        backend_api_url="http://backend:8000",
    )
    assert settings.environment is Environment.PRODUCTION
    assert settings.debug is False
