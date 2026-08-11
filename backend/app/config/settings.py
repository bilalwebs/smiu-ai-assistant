"""Application settings modeled with Pydantic Settings.

Purpose:
    Centralized, typed, environment-aware configuration for the backend service
    (BACKEND_ARCHITECTURE.md §7). Every environment (development, testing,
    production) has an isolated settings class; secrets and tunable values are
    read from environment variables and a local ``.env`` file only.

Responsibilities:
    - Validate configuration at startup (fail fast on malformed values).
    - Provide per-environment defaults and gates (docs exposure, log level,
      debug mode, database defaults).
    - Cache a single validated settings instance for the process.

Usage:
    ``settings = get_settings()`` returns the cached, validated instance.
    Tests may pass an explicit ``env_file`` or inject a ``TestingSettings``
    instance into :func:`app.core.app_factory.create_app`.

Environment variables:
    See ``backend/.env.example`` for the authoritative template. Every new
    variable must be added there when introduced (DEVELOPMENT_WORKFLOW.md §16.1).
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class Environment(str, Enum):
    """Supported runtime environments (BACKEND_ARCHITECTURE.md §7.4)."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Base configuration shared by every environment.

    Defaults represent a safe development posture; production overrides the
    security-critical values (docs disabled, log level ``INFO``, required DB).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    app_name: str = "smiu-ai-assistant-backend"
    version: str = "0.1.0"
    api_version: str = "1.0"

    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: str = "sqlite+aiosqlite:///./data/dev.db"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    request_id_header: str = "X-Request-Id"
    correlation_id_header: str = "X-Correlation-Id"

    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"

    # --- authentication ---------------------------------------------------
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "smiu-ai-assistant"
    jwt_audience: str = "smiu-ai-assistant-api"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    remember_me_expire_days: int = 30
    email_verification_expire_minutes: int = 1440
    password_reset_expire_minutes: int = 30
    lockout_threshold: int = 5
    lockout_minutes: int = 15
    frontend_base_url: str = "http://localhost:3000"
    frontend_reset_path: str = "reset-password"

    # --- rate limiting -------------------------------------------------------
    login_rate_limit: int = 10
    login_rate_window: int = 60
    register_rate_limit: int = 5
    register_rate_window: int = 300
    forgot_password_rate_limit: int = 5
    forgot_password_rate_window: int = 300
    reset_password_rate_limit: int = 5
    reset_password_rate_window: int = 300
    max_active_sessions: int = 10

    # --- email / SMTP -----------------------------------------------------
    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> Any:
        """Accept a comma-separated string from the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, value: Any) -> Any:
        normalized = str(value).upper()
        if normalized not in _VALID_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {', '.join(_VALID_LOG_LEVELS)}")
        return normalized

    @field_validator("jwt_algorithm", mode="after")
    @classmethod
    def _validate_jwt_algorithm(cls, value: str) -> str:
        if value.lower() == "none":
            raise ValueError("jwt_algorithm must not be 'none'")
        return value


class DevelopmentSettings(Settings):
    """Local development defaults (BACKEND_ARCHITECTURE.md §7.5)."""

    debug: bool = True
    log_level: str = "DEBUG"
    db_echo: bool = True
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"


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
    database_url: str = "sqlite+aiosqlite:///:memory:"


class ProductionSettings(Settings):
    """Production posture: docs gated, verbose logs disabled, secrets required."""

    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = Field(
        ...,
        description="Production PostgreSQL DSN; required and fail-fast when missing.",
    )
    jwt_secret: str = Field(
        ...,
        description="JWT signing secret; required and fail-fast when missing.",
    )
    docs_url: str | None = None
    redoc_url: str | None = None
    openapi_url: str | None = None

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret_production(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("jwt_secret must be at least 32 characters in production")
        if value == "dev-secret-change-me":
            raise ValueError("jwt_secret must not be the default dev value in production")
        return value


_SETTINGS_BY_ENVIRONMENT: dict[Environment, type[Settings]] = {
    Environment.DEVELOPMENT: DevelopmentSettings,
    Environment.TESTING: TestingSettings,
    Environment.PRODUCTION: ProductionSettings,
}

_SETTINGS_CACHE: dict[str, Settings] = {}


def get_settings(env_file: str | Path | None = None) -> Settings:
    """Return the validated, cached settings for the current environment.

    The ``ENVIRONMENT`` value (from the environment or the ``.env`` file)
    selects the settings class, so behaviour gates live in one place
    (BACKEND_ARCHITECTURE.md §7.4). Providing ``env_file`` overrides the
    ``.env`` file location, which is used by tests.
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
