"""Request and response schemas for executive report resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus import SimulationStatus

_REPORT_REQUEST_EXAMPLE: dict[str, Any] = {
    "simulation_id": "22222222-2222-2222-2222-222222222222",
    "title": "Executive summary for the HQ baseline run",
    "include_diagnostics": True,
}

_REPORT_RESPONSE_EXAMPLE: dict[str, Any] = {
    "simulation_id": "22222222-2222-2222-2222-222222222222",
    "building_id": "11111111-1111-1111-1111-111111111111",
    "building_name": "HQ Office Tower",
    "generated_at": "2026-07-26T10:30:00Z",
    "title": "Executive summary for the HQ baseline run",
    "executive_summary": (
        "The baseline office simulation completed successfully and produced normalized "
        "energy and comfort metrics for dashboard consumption."
    ),
    "final_status": "succeeded",
    "highlights": [
        "Total site energy: 15420.60 kWh",
        "Electricity consumption: 9630.20 kWh",
        "Average zone temperature: 23.40 C",
    ],
    "recommendations": ["Use this run as the reference baseline for future comparison reports."],
    "diagnostics": ["Expected EnergyPlus output artifact was not produced: eplusout.eso."],
}


class ReportCreateRequest(BaseModel):
    """HTTP contract for generating an executive report from simulation history."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _REPORT_REQUEST_EXAMPLE},
    )

    simulation_id: UUID
    title: str | None = Field(default=None, min_length=1, max_length=200)
    include_diagnostics: bool = True


class ExecutiveReportResponse(BaseModel):
    """HTTP response payload returned from the executive report endpoint."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _REPORT_RESPONSE_EXAMPLE},
    )

    simulation_id: UUID
    building_id: UUID | None = None
    building_name: str | None = None
    generated_at: datetime
    title: str
    executive_summary: str
    final_status: SimulationStatus
    highlights: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()


__all__ = ["ExecutiveReportResponse", "ReportCreateRequest"]
