from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from ecoloop_backend.api.dependencies import get_health_service
from ecoloop_backend.application.services.health_service import HealthService
from ecoloop_backend.domain.health import HealthReport, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "ecoloop-backend",
                "environment": "production",
                "version": "0.1.0",
                "checked_at": "2026-07-26T10:15:00Z",
            }
        },
    )

    status: HealthStatus
    service: str
    environment: str
    version: str
    checked_at: datetime


def _to_response(report: HealthReport) -> HealthResponse:
    return HealthResponse(
        status=report.status,
        service=report.service,
        environment=report.environment,
        version=report.version,
        checked_at=report.checked_at,
    )


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Return a lightweight liveness snapshot for orchestration and load balancers.",
)
def live(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    """Return a lightweight liveness snapshot for the backend process."""
    return _to_response(health_service.live())


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Return a readiness snapshot for the backend runtime and container.",
)
def ready(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    """Return a readiness snapshot for the backend runtime."""
    return _to_response(health_service.ready())
