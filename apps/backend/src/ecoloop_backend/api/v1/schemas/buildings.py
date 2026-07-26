"""Request and response schemas for building resources."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_BUILDING_CREATE_EXAMPLE: dict[str, Any] = {
    "name": "HQ Office Tower",
    "description": "Primary commercial office baseline for dashboard analytics.",
    "timezone": "Asia/Kolkata",
    "baseline_idf_path": "C:/ecoloop/buildings/hq-office.idf",
    "weather_file_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    "metadata": {
        "portfolio": "north-region",
        "building_type": "office",
    },
}

_BUILDING_DETAIL_EXAMPLE: dict[str, Any] = {
    "building_id": "11111111-1111-1111-1111-111111111111",
    "name": "HQ Office Tower",
    "description": "Primary commercial office baseline for dashboard analytics.",
    "timezone": "Asia/Kolkata",
    "created_at": "2026-07-26T10:15:00Z",
    "simulation_count": 2,
    "baseline_idf_path": "C:/ecoloop/buildings/hq-office.idf",
    "weather_file_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
    "metadata": {
        "portfolio": "north-region",
        "building_type": "office",
    },
}

_BUILDING_SUMMARY_EXAMPLE: dict[str, Any] = {
    "building_id": "11111111-1111-1111-1111-111111111111",
    "name": "HQ Office Tower",
    "description": "Primary commercial office baseline for dashboard analytics.",
    "timezone": "Asia/Kolkata",
    "created_at": "2026-07-26T10:15:00Z",
    "simulation_count": 2,
}


class BuildingCreateRequest(BaseModel):
    """HTTP contract for creating one dashboard-visible building resource."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _BUILDING_CREATE_EXAMPLE},
    )

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    timezone: str | None = None
    baseline_idf_path: Path | None = None
    weather_file_path: Path | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class BuildingSummaryResponse(BaseModel):
    """Summary payload returned in building collection endpoints."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _BUILDING_SUMMARY_EXAMPLE},
    )

    building_id: UUID
    name: str
    description: str | None = None
    timezone: str | None = None
    created_at: datetime
    simulation_count: int = Field(default=0, ge=0)


class BuildingDetailResponse(BuildingSummaryResponse):
    """Detailed building payload returned from create and detail endpoints."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"example": _BUILDING_DETAIL_EXAMPLE},
    )

    baseline_idf_path: Path | None = None
    weather_file_path: Path | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class BuildingListResponse(BaseModel):
    """Collection payload returned by the building list endpoint."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "count": 1,
                "items": [_BUILDING_SUMMARY_EXAMPLE],
            }
        },
    )

    count: int = Field(ge=0)
    items: tuple[BuildingSummaryResponse, ...] = ()


__all__ = [
    "BuildingCreateRequest",
    "BuildingDetailResponse",
    "BuildingListResponse",
    "BuildingSummaryResponse",
]
