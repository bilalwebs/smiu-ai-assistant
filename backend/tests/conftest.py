"""Shared test fixtures and environment setup (TESTING_STRATEGY.md §27).

Environment:
    Forces ``ENVIRONMENT=testing`` before the app is imported so every test
    runs against ``TestingSettings`` (in-memory SQLite, no ``.env`` file), and
    resets the settings/engine caches between tests.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "testing"

from app.config.settings import clear_settings_cache
from app.core.app_factory import create_app
from app.database.session import reset_engine


@pytest.fixture()
def client() -> object:
    """Yield a TestClient with lifespan running and caches reset on teardown."""
    clear_settings_cache()
    reset_engine()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    clear_settings_cache()
    reset_engine()
