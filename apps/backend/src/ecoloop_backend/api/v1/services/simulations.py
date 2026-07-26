"""Backend service for simulation execution and history queries."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from logging import Logger
from uuid import UUID

from ecoloop_backend.api.v1.schemas.simulations import (
    SimulationDetailResponse,
    SimulationListResponse,
    SimulationRunRequest,
    SimulationSummaryResponse,
)
from ecoloop_backend.api.v1.services.state import BackendRuntimeState
from ecoloop_common.exceptions import ValidationError
from ecoloop_energyplus import SimulationService, SimulationSpec

type Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class SimulationApiService:
    """Execute EnergyPlus simulations and retain queryable history for the API layer."""

    def __init__(
        self,
        *,
        state: BackendRuntimeState,
        simulation_service: SimulationService,
        logger: Logger,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the service with shared runtime state and platform orchestration."""
        self._state = state
        self._simulation_service = simulation_service
        self._logger = logger
        self._clock = clock or _utc_now

    def run_simulation(self, request: SimulationRunRequest) -> SimulationDetailResponse:
        """Execute one simulation through the shared platform and store the result."""
        with self._state.lock:
            if request.building_id is not None and request.building_id not in self._state.buildings:
                raise ValidationError(
                    "The specified building_id does not exist.",
                    context={"field": "building_id", "value": str(request.building_id)},
                )

        self._logger.info(
            "Simulation execution started",
            extra={
                "event": "simulation_execution_started",
                "building_id": str(request.building_id) if request.building_id else None,
                "idf_path": str(request.idf_path),
                "epw_path": str(request.epw_path),
            },
        )
        result = self._simulation_service.run(
            SimulationSpec(
                idf_path=request.idf_path,
                epw_path=request.epw_path,
                timeout_seconds=request.timeout_seconds,
                parallel_jobs=request.parallel_jobs,
            )
        )
        created_at = result.metadata.started_at or self._clock()
        detail = SimulationDetailResponse(
            simulation_id=result.simulation_id,
            building_id=request.building_id,
            final_status=result.final_status,
            created_at=created_at,
            idf_path=request.idf_path,
            epw_path=request.epw_path,
            duration_ms=result.metadata.duration_ms,
            energyplus_version=result.metadata.energyplus_version,
            diagnostics_count=len(result.diagnostics),
            result=result,
        )
        with self._state.lock:
            self._state.simulations[detail.simulation_id] = detail

        self._logger.info(
            "Simulation execution completed",
            extra={
                "event": "simulation_execution_completed",
                "simulation_id": str(detail.simulation_id),
                "final_status": detail.final_status.value,
                "duration_ms": detail.duration_ms,
            },
        )
        return detail

    def list_simulations(self) -> SimulationListResponse:
        """Return the full simulation history sorted by newest creation time first."""
        with self._state.lock:
            items = tuple(
                self._to_summary(detail)
                for detail in sorted(
                    self._state.simulations.values(),
                    key=lambda simulation: simulation.created_at,
                    reverse=True,
                )
            )

        return SimulationListResponse(count=len(items), items=items)

    def get_simulation(self, simulation_id: UUID) -> SimulationDetailResponse | None:
        """Return one stored simulation result by identifier when available."""
        with self._state.lock:
            return self._state.simulations.get(simulation_id)

    @staticmethod
    def _to_summary(detail: SimulationDetailResponse) -> SimulationSummaryResponse:
        """Project one stored simulation detail into a history list item."""
        return SimulationSummaryResponse(
            simulation_id=detail.simulation_id,
            building_id=detail.building_id,
            final_status=detail.final_status,
            created_at=detail.created_at,
            idf_path=detail.idf_path,
            epw_path=detail.epw_path,
            duration_ms=detail.duration_ms,
            energyplus_version=detail.energyplus_version,
            diagnostics_count=detail.diagnostics_count,
        )


__all__ = ["SimulationApiService"]
