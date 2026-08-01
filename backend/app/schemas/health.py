"""Health-check schemas (API_SPECIFICATION.md §24; DEPLOYMENT.md §20).

Purpose:
    Define the payloads for the liveness, readiness, combined summary, and
    version endpoints.

Responsibilities:
    - Model each health payload with typed fields.
    - Keep health metadata non-sensitive (no secrets, no PII).

Usage:
    Used as the ``data`` type parameter of ``SuccessResponse`` on the health
    router (``app.api.v1.endpoints.health``).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class CheckStatus(str, Enum):
    """Status of the service or a single dependency check."""

    UP = "up"
    DOWN = "down"


class ComponentCheck(BaseModel):
    """Result of checking one dependency (e.g., database)."""

    name: str
    status: CheckStatus
    message: str | None = None


class LivenessData(BaseModel):
    """Liveness payload: process is running."""

    status: CheckStatus = CheckStatus.UP
    version: str
    message: str = "Service is alive"


class ReadinessData(BaseModel):
    """Readiness payload: dependencies reachable or not."""

    status: CheckStatus
    checks: list[ComponentCheck]
    message: str


class HealthSummaryData(BaseModel):
    """Combined health summary payload."""

    overall: CheckStatus
    liveness: LivenessData
    readiness: ReadinessData


class ServiceVersionData(BaseModel):
    """Non-sensitive build/version metadata (API_SPECIFICATION.md §24)."""

    name: str
    version: str
    api_version: str
    environment: str
    python_version: str
