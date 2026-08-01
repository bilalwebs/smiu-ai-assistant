"""CORS middleware registration.

Purpose:
    Enable Cross-Origin Resource Sharing for the configured frontend origins
    (BACKEND_ARCHITECTURE.md §17; API_SPECIFICATION.md §6.3).

Responsibilities:
    - Add CORSMiddleware using settings-driven allow_origins, methods, headers.
    - Disallow credentials when using explicit origins (safe combination).
    - Default to a permissive development origin set in non-production.

Usage:
    ``register_cors(app, settings)`` is called by the application factory.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config.settings import Settings

# Methods allowed on API routes; configured here so every origin shares them.
_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# Header names the server may read back from cross-origin requests.
_ALLOW_HEADERS = ["*"]

_DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def register_cors(app: FastAPI, settings: Settings) -> None:
    """Register CORS middleware using the application settings."""
    from fastapi.middleware.cors import CORSMiddleware

    origins = list(settings.cors_origins or _DEFAULT_DEV_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=_ALLOW_METHODS,
        allow_headers=_ALLOW_HEADERS,
    )
