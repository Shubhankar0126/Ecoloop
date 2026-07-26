"""REST router for building collection and detail resources."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ecoloop_backend.api.error_models import ProblemDetails
from ecoloop_backend.api.v1.dependencies import get_building_service
from ecoloop_backend.api.v1.schemas.buildings import (
    BuildingCreateRequest,
    BuildingDetailResponse,
    BuildingListResponse,
)
from ecoloop_backend.api.v1.services import BuildingCatalogService

router = APIRouter(prefix="/buildings", tags=["buildings"])

_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "model": ProblemDetails,
        "description": "The requested building resource does not exist.",
    }
}


@router.get(
    "",
    response_model=BuildingListResponse,
    summary="List buildings",
    description="Return every building resource currently known to the backend runtime.",
)
def list_buildings(
    building_service: Annotated[BuildingCatalogService, Depends(get_building_service)],
) -> BuildingListResponse:
    """Return the building collection for dashboard initialization and navigation."""
    return building_service.list_buildings()


@router.post(
    "",
    response_model=BuildingDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create building",
    description=(
        "Create one building resource that can later be referenced by simulations and reports."
    ),
    responses={
        400: {
            "model": ProblemDetails,
            "description": "The request body failed domain validation.",
        }
    },
)
def create_building(
    request: BuildingCreateRequest,
    building_service: Annotated[BuildingCatalogService, Depends(get_building_service)],
) -> BuildingDetailResponse:
    """Create one building resource inside the process-local backend catalog."""
    return building_service.create_building(request)


@router.get(
    "/{building_id}",
    response_model=BuildingDetailResponse,
    summary="Get building details",
    description="Return the complete building resource for one identifier.",
    responses=_NOT_FOUND_RESPONSES,
)
def get_building(
    building_id: UUID,
    building_service: Annotated[BuildingCatalogService, Depends(get_building_service)],
) -> BuildingDetailResponse:
    """Return one stored building resource or a 404 problem details response."""
    building = building_service.get_building(building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found.")

    return building


__all__ = ["router"]
