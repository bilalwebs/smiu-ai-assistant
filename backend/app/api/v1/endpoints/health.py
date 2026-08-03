"""Health/readiness/liveness endpoints.

Purpose:
    Provide operational health, liveness, readiness, and version endpoints
    (API_SPECIFICATION.md §24; DEPLOYMENT.md §20).

Responsibilities:
    - ``/health/live``: always 200 while the process is up.
    - ``/health/ready``: checks DB connectivity; 503 with details when degraded.
    - ``/health``: combined summary of liveness + readiness.
    - ``/health/version``: running service version metadata.
    - Serve the same handlers under the orchestration alias path.

Usage:
    Included in :mod:`app.api.v1`; the application factory also mounts the
    orchestration aliases.
"""

from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.database.health import check_database_health
from app.dependencies.database import get_db_session
from app.dependencies.settings import get_settings
from app.schemas.health import (
    CheckStatus,
    ComponentCheck,
    HealthSummaryData,
    LivenessData,
    ReadinessData,
    ServiceVersionData,
)
from app.schemas.response import SuccessResponse
from app.utils.response import success_response

router = APIRouter(tags=["health"])

_LIVENESS_MSG = "Service is alive"
_READY_MSG = "Service is ready"
_DB_NOT_READY_MSG = "Database is not reachable"
_DB_REACHABLE_MSG = "Database reachable"


@router.get(
    "/health/live",
    response_model=SuccessResponse[LivenessData],
    summary="Liveness probe",
)
async def liveness(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[LivenessData]:
    """Return 200 while the service process is running."""
    return success_response(
        request,
        LivenessData(status=CheckStatus.UP, version=settings.version, message=_LIVENESS_MSG),
    )


async def _check_db(session: AsyncSession) -> ComponentCheck:
    health = await check_database_health(session)
    if health.is_up:
        return ComponentCheck(
            name="database", status=CheckStatus.UP, message=_DB_REACHABLE_MSG
        )
    return ComponentCheck(
        name="database", status=CheckStatus.DOWN, message=_DB_NOT_READY_MSG
    )


@router.get(
    "/health/ready",
    response_model=SuccessResponse[ReadinessData],
    summary="Readiness probe",
)
async def readiness(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReadinessData] | JSONResponse:
    """Return 200 when dependencies are reachable, else 503 with details."""
    component = await _check_db(db)
    ready = component.status is CheckStatus.UP
    data = ReadinessData(
        status=CheckStatus.UP if ready else CheckStatus.DOWN,
        checks=[component],
        message=_READY_MSG if ready else _DB_NOT_READY_MSG,
    )
    response = success_response(request, data)
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(response),
        )
    return response


@router.get(
    "/health",
    response_model=SuccessResponse[HealthSummaryData],
    summary="Combined health summary",
)
async def health(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[HealthSummaryData] | JSONResponse:
    """Return a combined liveness + readiness summary."""
    component = await _check_db(db)
    ready = component.status is CheckStatus.UP
    live_data = LivenessData(
        status=CheckStatus.UP, version=settings.version, message=_LIVENESS_MSG
    )
    ready_data = ReadinessData(
        status=CheckStatus.UP if ready else CheckStatus.DOWN,
        checks=[component],
        message=_READY_MSG if ready else _DB_NOT_READY_MSG,
    )
    summary = HealthSummaryData(
        overall=CheckStatus.UP if ready else CheckStatus.DOWN,
        liveness=live_data,
        readiness=ready_data,
    )
    response = success_response(request, summary)
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(response),
        )
    return response


@router.get(
    "/health/version",
    response_model=SuccessResponse[ServiceVersionData],
    summary="Service version",
)
async def version(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[ServiceVersionData]:
    """Return running service version metadata."""
    return success_response(
        request,
        ServiceVersionData(
            name=settings.app_name,
            version=settings.version,
            api_version=settings.api_version,
            environment=settings.environment.value,
            python_version=sys.version.split()[0],
        ),
    )


orchestration_router = APIRouter(tags=["health"], include_in_schema=False)


@orchestration_router.get(
    "/health/live",
    response_model=SuccessResponse[LivenessData],
)
async def _health_live_alias(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[LivenessData]:
    """Orchestration alias for ``/health/live`` (DEPLOYMENT.md §20)."""
    return await liveness(request, settings)


@orchestration_router.get(
    "/health/ready",
    response_model=SuccessResponse[ReadinessData],
)
async def _health_ready_alias(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReadinessData] | JSONResponse:
    """Orchestration alias for ``/health/ready`` (DEPLOYMENT.md §20)."""
    return await readiness(request, db)


@orchestration_router.get(
    "/health",
    response_model=SuccessResponse[HealthSummaryData],
)
async def _health_summary_alias(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[HealthSummaryData] | JSONResponse:
    """Orchestration alias for ``/health`` (DEPLOYMENT.md §20)."""
    return await health(request, db, settings)


@orchestration_router.get(
    "/health/version",
    response_model=SuccessResponse[ServiceVersionData],
)
async def _health_version_alias(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SuccessResponse[ServiceVersionData]:
    """Orchestration alias for ``/health/version`` (DEPLOYMENT.md §20)."""
    return await version(request, settings)
