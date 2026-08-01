"""Settings and configuration tests (BACKEND_ARCHITECTURE.md §7).

Imports the settings module rather than its classes to avoid pytest collecting
the ``TestingSettings`` class as a test class.
"""

from __future__ import annotations

from pytest import MonkeyPatch

import app.config.settings as cs


def test_testing_settings_selected(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "testing")
    cs.clear_settings_cache()
    settings = cs.get_settings()
    assert isinstance(settings, cs.TestingSettings)
    assert settings.environment is cs.Environment.TESTING
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"
    assert settings.docs_url == "/docs"


def test_cors_origins_comma_separated() -> None:
    settings = cs.TestingSettings(
        cors_origins="http://localhost:3000,http://127.0.0.1:5173"
    )
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:5173"]


def test_invalid_log_level_rejected() -> None:
    try:
        cs.Settings(log_level="VERBOSE")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid LOG_LEVEL")
