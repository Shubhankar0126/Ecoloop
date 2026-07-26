"""REST router for simulation execution and history resources."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ecoloop_backend.api.error_models import ProblemDetails
from ecoloop_backend.api.v1.dependencies import get_simulation_api_service
from ecoloop_backend.api.v1.schemas.simulations import (
    SimulationDetailResponse,
    SimulationListResponse,
    SimulationRunRequest,
)
from ecoloop_backend.api.v1.services import SimulationApiService

router = APIRouter(prefix="/simulations", tags=["simulations"])

_SIMULATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ProblemDetails,
        "description": "The simulation request failed domain or input validation.",
    },
    404: {
        "model": ProblemDetails,
        "description": "The requested simulation history resource does not exist.",
    },
    500: {
        "model": ProblemDetails,
        "description": "The backend could not complete the requested simulation operation.",
    },
    503: {
        "model": ProblemDetails,
        "description": "A required infrastructure dependency was unavailable.",
    },
}


@router.post(
    "",
    response_model=SimulationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run simulation",
    description=(
        "Execute one EnergyPlus simulation through the shared SimulationService "
        "and store the normalized result in runtime history."
    ),
    responses=_SIMULATION_RESPONSES,
)
def run_simulation(
    request: SimulationRunRequest,
    simulation_service: Annotated[SimulationApiService, Depends(get_simulation_api_service)],
) -> SimulationDetailResponse:
    """Execute one simulation request and return the normalized result resource."""
    return simulation_service.run_simulation(request)


@router.get(
    "",
    response_model=SimulationListResponse,
    summary="List simulation history",
    description=(
        "Return the in-process history of simulations executed through this backend runtime."
    ),
)
def list_simulations(
    simulation_service: Annotated[SimulationApiService, Depends(get_simulation_api_service)],
) -> SimulationListResponse:
    """Return the simulation history collection for dashboard list views."""
    return simulation_service.list_simulations()


@router.get(
    "/{simulation_id}",
    response_model=SimulationDetailResponse,
    summary="Get simulation result",
    description="Return the complete normalized simulation result for one recorded execution.",
    responses=_SIMULATION_RESPONSES,
)
def get_simulation(
    simulation_id: UUID,
    simulation_service: Annotated[SimulationApiService, Depends(get_simulation_api_service)],
) -> SimulationDetailResponse:
    """Return one stored simulation record or a 404 problem details response."""
    simulation = simulation_service.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")

    return simulation


__all__ = ["router"]
