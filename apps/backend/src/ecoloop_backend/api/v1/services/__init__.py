"""Backend-only REST adapter services for the EcoLoop v1 API."""

from ecoloop_backend.api.v1.services.ai import AiChatService
from ecoloop_backend.api.v1.services.buildings import BuildingCatalogService
from ecoloop_backend.api.v1.services.reports import ExecutiveReportService
from ecoloop_backend.api.v1.services.simulations import SimulationApiService
from ecoloop_backend.api.v1.services.state import BackendRuntimeState

__all__ = [
    "AiChatService",
    "BackendRuntimeState",
    "BuildingCatalogService",
    "ExecutiveReportService",
    "SimulationApiService",
]
