"""Backend service for managing dashboard-facing building resources."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from logging import Logger
from uuid import UUID, uuid4

from ecoloop_backend.api.v1.schemas.buildings import (
    BuildingCreateRequest,
    BuildingDetailResponse,
    BuildingListResponse,
    BuildingSummaryResponse,
)
from ecoloop_backend.api.v1.services.state import BackendRuntimeState

type Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class BuildingCatalogService:
    """Manage the process-local catalog of buildings exposed through the REST API."""

    def __init__(
        self,
        *,
        state: BackendRuntimeState,
        logger: Logger,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the service with shared runtime state and logging."""
        self._state = state
        self._logger = logger
        self._clock = clock or _utc_now

    def list_buildings(self) -> BuildingListResponse:
        """Return the full building collection sorted by name."""
        with self._state.lock:
            items = tuple(
                self._to_summary(record)
                for record in sorted(
                    self._state.buildings.values(),
                    key=lambda building: (building.name.casefold(), building.created_at),
                )
            )

        return BuildingListResponse(count=len(items), items=items)

    def create_building(self, request: BuildingCreateRequest) -> BuildingDetailResponse:
        """Create and persist one building resource in process-local runtime state."""
        building = BuildingDetailResponse(
            building_id=uuid4(),
            name=request.name,
            description=request.description,
            timezone=request.timezone,
            created_at=self._clock(),
            simulation_count=0,
            baseline_idf_path=request.baseline_idf_path,
            weather_file_path=request.weather_file_path,
            metadata=request.metadata,
        )
        with self._state.lock:
            self._state.buildings[building.building_id] = building

        self._logger.info(
            "Building created",
            extra={
                "event": "building_created",
                "building_id": str(building.building_id),
                "building_name": building.name,
            },
        )
        return building

    def get_building(self, building_id: UUID) -> BuildingDetailResponse | None:
        """Return one building resource by identifier when it exists."""
        with self._state.lock:
            building = self._state.buildings.get(building_id)

        if building is None:
            return None

        return building.model_copy(update={"simulation_count": self._simulation_count(building_id)})

    def exists(self, building_id: UUID) -> bool:
        """Return whether one building identifier exists in the catalog."""
        with self._state.lock:
            return building_id in self._state.buildings

    def get_building_name(self, building_id: UUID) -> str | None:
        """Return one building name when the identifier exists."""
        with self._state.lock:
            building = self._state.buildings.get(building_id)

        return None if building is None else building.name

    def _to_summary(self, building: BuildingDetailResponse) -> BuildingSummaryResponse:
        """Project one stored building resource into a list-friendly summary."""
        simulation_count = self._simulation_count(building.building_id)
        return BuildingSummaryResponse(
            building_id=building.building_id,
            name=building.name,
            description=building.description,
            timezone=building.timezone,
            created_at=building.created_at,
            simulation_count=simulation_count,
        )

    def _simulation_count(self, building_id: UUID) -> int:
        """Count how many recorded simulations reference one building identifier."""
        with self._state.lock:
            return sum(
                1
                for simulation in self._state.simulations.values()
                if simulation.building_id == building_id
            )


__all__ = ["BuildingCatalogService"]
