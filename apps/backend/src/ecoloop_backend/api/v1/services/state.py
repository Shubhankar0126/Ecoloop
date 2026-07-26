"""Process-local runtime state shared by the backend API adapter services."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID

from ecoloop_backend.api.v1.schemas.buildings import BuildingDetailResponse
from ecoloop_backend.api.v1.schemas.simulations import SimulationDetailResponse


@dataclass(slots=True)
class BackendRuntimeState:
    """Mutable process-local state for API resources until persistence is introduced."""

    buildings: dict[UUID, BuildingDetailResponse] = field(default_factory=dict)
    simulations: dict[UUID, SimulationDetailResponse] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


__all__ = ["BackendRuntimeState"]
