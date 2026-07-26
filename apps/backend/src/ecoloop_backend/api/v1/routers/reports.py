"""REST router for deterministic executive report generation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ecoloop_backend.api.error_models import ProblemDetails
from ecoloop_backend.api.v1.dependencies import get_report_service
from ecoloop_backend.api.v1.schemas.reports import ExecutiveReportResponse, ReportCreateRequest
from ecoloop_backend.api.v1.services import ExecutiveReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "",
    response_model=ExecutiveReportResponse,
    summary="Generate executive report",
    description=(
        "Generate a deterministic executive report from one recorded simulation "
        "result for dashboard consumption."
    ),
    responses={
        404: {
            "model": ProblemDetails,
            "description": "The requested simulation history resource does not exist.",
        },
        400: {
            "model": ProblemDetails,
            "description": "The report request payload failed validation.",
        },
    },
)
def generate_report(
    request: ReportCreateRequest,
    report_service: Annotated[ExecutiveReportService, Depends(get_report_service)],
) -> ExecutiveReportResponse:
    """Generate one executive report or return a 404 problem details response."""
    report = report_service.generate_report(request)
    if report is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    return report


__all__ = ["router"]
