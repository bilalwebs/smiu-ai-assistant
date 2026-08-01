"""Backend configuration package.

Purpose:
    Owns Pydantic Settings-based configuration for the backend service.

Responsibilities:
    - Expose the settings model hierarchy (base + per-environment classes).
    - Load configuration from environment variables and a local ``.env`` file.
    - Provide a cached, typed accessor used by the application factory.

Usage:
    Import ``get_settings`` to obtain the validated singleton, or import the
    ``Settings`` base class for typing and the environment classes for tests.
"""
