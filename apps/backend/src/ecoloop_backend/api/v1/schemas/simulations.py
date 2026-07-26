"""Request and response schemas for simulation resources."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus import SimulationResult, SimulationStatus

_SIMULATION_RUN_REQUEST_EXAMPLE: dict[str, Any] = {
    "building_id": "11111111-1111-1111-1111-111111111111",
    "idf_path": "C:/ecoloop/buildings/hq-office.idf",
    "epw_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    "timeout_seconds": 1800,
    "parallel_jobs": 1,
}

_SIMULATION_SUMMARY_EXAMPLE: dict[str, Any] = {
    "simulation_id": "22222222-2222-2222-2222-222222222222",
    "building_id": "11111111-1111-1111-1111-111111111111",
    "final_status": "succeeded",
    "created_at": "2026-07-26T10:20:00Z",
    "idf_path": "C:/ecoloop/buildings/hq-office.idf",
    "epw_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    "duration_ms": 41234,
    "energyplus_version": "24.2.0",
    "diagnostics_count": 1,
}

_SIMULATION_DETAIL_EXAMPLE: dict[str, Any] = {
    **_SIMULATION_SUMMARY_EXAMPLE,
    "result": {
        "simulation_id": "22222222-2222-2222-2222-222222222222",
        "final_status": "succeeded",
        "metrics": {
            "values": {},
            "energy": {
                "total_site_energy_kwh": 15420.6,
                "electricity_consumption_kwh": 9630.2,
            },
            "hvac": {
                "heating_energy_kwh": 2410.4,
                "cooling_energy_kwh": 3188.1,
                "hvac_energy_kwh": 5598.5,
                "equipment_loads_kwh": 744.0,
            },
            "comfort": {
                "average_zone_temperature_celsius": 23.4,
                "average_zone_humidity_percent": 48.2,
                "average_pmv": 0.1,
                "average_ppd_percent": 9.8,
            },
            "weather": None,
            "zones": [],
            "monthly_summary": [],
            "annual_summary": [],
        },
        "artifacts": [],
        "diagnostics": ["Expected EnergyPlus output artifact was not produced: eplusout.eso."],
        "metadata": {
            "energyplus_version": "24.2.0",
            "installation_root": "C:/EnergyPlusV24-2-0",
            "command_line": [
                "energyplus",
                "-w",
                "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
            ],
            "exit_code": 0,
            "duration_ms": 41234,
            "idf_checksum": "abc123",
            "epw_checksum": "def456",
            "hostname": "ecoloop-runner",
            "started_at": "2026-07-26T10:20:00Z",
            "completed_at": "2026-07-26T10:20:41Z",
        },
    },
}


class SimulationRunRequest(BaseModel):
    """HTTP contract for launching one EnergyPlus simulation."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _SIMULATION_RUN_REQUEST_EXAMPLE},
    )

    building_id: UUID | None = None
    idf_path: Path
    epw_path: Path
    timeout_seconds: int | None = Field(default=None, ge=1)
    parallel_jobs: int | None = Field(default=None, ge=1)


class SimulationSummaryResponse(BaseModel):
    """Summary payload returned in simulation history endpoints."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _SIMULATION_SUMMARY_EXAMPLE},
    )

    simulation_id: UUID
    building_id: UUID | None = None
    final_status: SimulationStatus
    created_at: datetime
    idf_path: Path
    epw_path: Path
    duration_ms: int | None = Field(default=None, ge=0)
    energyplus_version: str | None = None
    diagnostics_count: int = Field(default=0, ge=0)


class SimulationDetailResponse(SimulationSummaryResponse):
    """Detailed simulation payload returned from create and detail endpoints."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _SIMULATION_DETAIL_EXAMPLE},
    )

    result: SimulationResult


class SimulationListResponse(BaseModel):
    """Collection payload returned from the simulation history endpoint."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "count": 1,
                "items": [_SIMULATION_SUMMARY_EXAMPLE],
            }
        },
    )

    count: int = Field(ge=0)
    items: tuple[SimulationSummaryResponse, ...] = ()


__all__ = [
    "SimulationDetailResponse",
    "SimulationListResponse",
    "SimulationRunRequest",
    "SimulationSummaryResponse",
]
