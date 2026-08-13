"""AI service configuration modeled with Pydantic Settings.

Purpose:
    Centralized, typed, environment-aware configuration for the AI service
    (AI_ARCHITECTURE.md §2.2, §35; BACKEND_ARCHITECTURE.md §20). Values are
    read from environment variables and a local ``.env`` file only. Loading
    configuration never calls external services and never initializes LLM
    clients, so imports remain safe for tests.

Sources:
    - Model selection / gateway: AI_ARCHITECTURE.md §35 — a provider-agnostic
      LLM gateway behind a single selection (``LLM_PROVIDER``), config-driven
      model id per provider, low-temperature factuality default, max-token
      response cap, bounded retry policy, and a config-driven in-provider
      fallback model (§35.6).
    - Embeddings: AI_ARCHITECTURE.md §15.1 — Sentence Transformers encoder;
      the same model must embed queries and documents.
    - RAG: AI_ARCHITECTURE.md §16.5 (``RAG_TOP_K`` default 4); knowledge root
      and FAISS location per AI_ARCHITECTURE.md §2.2 and BACKEND_ARCHITECTURE.md
      §5.3 (``knowledge/`` and ``knowledge/vectorstore/``).
    - Memory: AI_ARCHITECTURE.md §17.3, §21.6 — ``CHAT_HISTORY_LIMIT`` turns
      (default 20).
    - Integration boundary: BACKEND_ARCHITECTURE.md §20 — the AI layer is a
      first-class boundary; persistence flows through the backend service.

Environment variables:
    See ``ai/.env.example`` for the scaffold template; this module honors the
    variables corresponding to the fields below.

Usage:
    ``settings = get_settings()`` returns the cached, validated instance.
    Tests inject a ``TestingSettings`` (no ``.env`` file) for determinism.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class Environment(StrEnum):
    """Supported runtime environments (BACKEND_ARCHITECTURE.md §7.4)."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LLMProvider(StrEnum):
    """Supported LLM providers behind the gateway (AI_ARCHITECTURE.md §35.1).

    The Coordinator and the workflow never reference a provider directly; the
    active provider is chosen from configuration (``LLM_PROVIDER``).
    """

    GEMINI = "gemini"
    OPENAI = "openai"
    GROQ = "groq"


# Settings field holding the default model id per provider. The per-provider
# defaults mirror §35.2 (``GEMINI_MODEL``/``OPENAI_MODEL``/``GROQ_MODEL``);
# ``LLM_MODEL`` overrides the active provider's model without touching these.
_PROVIDER_MODEL_FIELDS: dict[LLMProvider, str] = {
    LLMProvider.GEMINI: "gemini_model",
    LLMProvider.OPENAI: "openai_model",
    LLMProvider.GROQ: "groq_model",
}

# API key field on Settings per provider; read by ``api_key_for``.
_PROVIDER_KEY_FIELDS: dict[LLMProvider, str] = {
    LLMProvider.GEMINI: "gemini_api_key",
    LLMProvider.OPENAI: "openai_api_key",
    LLMProvider.GROQ: "groq_api_key",
}


class Settings(BaseSettings):
    """Base configuration shared by every environment.

    Defaults represent a safe development posture; the production subclass
    requires the connection-critical values to be provided explicitly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    app_name: str = "smiu-ai-assistant-ai"
    version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8001

    log_level: str = "INFO"

    # --- LLM gateway (AI_ARCHITECTURE.md §35) ------------------------------
    # Active provider behind the gateway; selection is configuration-driven and
    # never encoded in the Coordinator (§35.1).
    llm_provider: LLMProvider = LLMProvider.GEMINI
    # API keys per provider. Only the active provider's key is required; the
    # others may stay empty. The gateway factory enforces this at construction
    # time, never at Settings import.
    gemini_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    # Provider-appropriate default model ids (§35.2). ``llm_model`` (LLM_MODEL)
    # overrides the active provider's default when set.
    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.1-8b-instant"
    # Generic active-model override; empty means "use the provider default".
    llm_model: str = ""
    # Fallback model selected transparently when the primary is unavailable
    # (§35.6); in-provider only, selection is configuration-driven, never
    # hardcoded.
    llm_fallback_model: str | None = None
    # Factuality-first temperature for grounded answers and classification
    # (§35.3).
    llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    # Per-task response cap, bounded by the global context budget (§35.4).
    llm_max_tokens: int = Field(default=1024, gt=0)
    # Bounded exponential-backoff retries for transient errors (§23.3, §35.5).
    llm_max_retries: int = Field(default=2, ge=0)
    # Per-call timeout for LLM invocation (§23.1).
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)

    # --- Embeddings (AI_ARCHITECTURE.md §15.1) -----------------------------
    # Sentence Transformers encoder used for both queries and documents (model
    # parity fixed at index build time). Required in production; the exact
    # model is chosen at deployment, not hardcoded here.
    embedding_model: str = ""

    # --- RAG (AI_ARCHITECTURE.md §14-19) -----------------------------------
    # Top-K retrieved chunks per query, configurable per agent (§16.5).
    rag_top_k: int = Field(default=4, gt=0)
    # Global context budget for grounded generation — model context window minus
    # a reserved safety margin (§17.3, §35.4). The Context Builder trims to this.
    context_budget_tokens: int = Field(default=4096, gt=0)
    # Source documents by category (§2.2, BACKEND_ARCHITECTURE.md §5.3).
    knowledge_root: str = "knowledge"
    # FAISS index location (§2.2, §15.2; BACKEND_ARCHITECTURE.md §5.3).
    vector_store_path: str = "knowledge/vectorstore"

    # --- Memory (AI_ARCHITECTURE.md §17.3, §21.6) --------------------------
    # Recent turns injected into context (short-term memory window).
    chat_history_limit: int = Field(default=20, gt=0)

    # --- Integration boundary (BACKEND_ARCHITECTURE.md §20) ----------------
    # Backend service through which the AI layer persists (never direct writes).
    backend_api_url: str = "http://localhost:8000"

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, value: object) -> str:
        normalized = str(value).upper()
        if normalized not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {', '.join(_VALID_LOG_LEVELS)}")
        return normalized

    def active_model(self, provider: LLMProvider | None = None) -> str:
        """Resolve the model id used for a provider (§35.2).

        ``llm_model`` (``LLM_MODEL``) overrides the provider's default when set;
        otherwise the provider's own ``*_MODEL`` value is returned (itself
        defaulting to the provider-appropriate model).
        """
        resolved = provider if provider is not None else self.llm_provider
        if self.llm_model:
            return self.llm_model
        return str(getattr(self, _PROVIDER_MODEL_FIELDS[resolved]))

    def api_key_for(self, provider: LLMProvider | None = None) -> str:
        """Return the API key configured for a provider (``""`` when unset)."""
        resolved = provider if provider is not None else self.llm_provider
        return str(getattr(self, _PROVIDER_KEY_FIELDS[resolved]))


class DevelopmentSettings(Settings):
    """Local development defaults (BACKEND_ARCHITECTURE.md §7.5)."""

    debug: bool = True
    log_level: str = "DEBUG"


class TestingSettings(Settings):
    """Isolated settings for automated test suites (TESTING_STRATEGY.md §27).

    No ``.env`` file is read so tests are deterministic and never depend on
    developer-local configuration.
    """

    __test__ = False

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Environment.TESTING
    debug: bool = True
    log_level: str = "DEBUG"


class ProductionSettings(Settings):
    """Production posture: verbose logs disabled, connection-critical values required."""

    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: str = "INFO"
    embedding_model: str = Field(
        ...,
        min_length=1,
        description=(
            "Sentence Transformers model for queries and documents "
            "(AI_ARCHITECTURE.md §15.1)."
        ),
    )
    backend_api_url: str = Field(
        ...,
        min_length=1,
        description=(
            "Backend service URL; required and fail-fast when missing "
            "(BACKEND_ARCHITECTURE.md §20)."
        ),
    )


_SETTINGS_BY_ENVIRONMENT: dict[Environment, type[Settings]] = {
    Environment.DEVELOPMENT: DevelopmentSettings,
    Environment.TESTING: TestingSettings,
    Environment.PRODUCTION: ProductionSettings,
}

_SETTINGS_CACHE: dict[str, Settings] = {}


def get_settings(env_file: str | Path | None = None) -> Settings:
    """Return the validated, cached settings for the current environment.

    The ``ENVIRONMENT`` value (from the environment or the ``.env`` file)
    selects the settings class (BACKEND_ARCHITECTURE.md §7.4). Providing
    ``env_file`` overrides the ``.env`` file location, which is used by tests.
    """
    cache_key = "default" if env_file is None else os.fspath(env_file)
    cached = _SETTINGS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    probe = Settings(_env_file=env_file) if env_file is not None else Settings()
    settings_cls = _SETTINGS_BY_ENVIRONMENT[probe.environment]
    settings = settings_cls(_env_file=env_file) if env_file is not None else settings_cls()
    _SETTINGS_CACHE[cache_key] = settings
    return settings


def clear_settings_cache() -> None:
    """Drop cached settings; used by tests to reset configuration state."""
    _SETTINGS_CACHE.clear()
