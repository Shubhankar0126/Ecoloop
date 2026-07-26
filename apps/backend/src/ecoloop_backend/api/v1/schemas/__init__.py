"""Versioned HTTP schemas for the EcoLoop backend API."""

from ecoloop_backend.api.v1.schemas.ai import AiChatRequest, AiChatResponse
from ecoloop_backend.api.v1.schemas.buildings import (
    BuildingCreateRequest,
    BuildingDetailResponse,
    BuildingListResponse,
    BuildingSummaryResponse,
)
from ecoloop_backend.api.v1.schemas.reports import (
    ExecutiveReportResponse,
    ReportCreateRequest,
)
from ecoloop_backend.api.v1.schemas.simulations import (
    SimulationDetailResponse,
    SimulationListResponse,
    SimulationRunRequest,
    SimulationSummaryResponse,
)

__all__ = [
    "AiChatRequest",
    "AiChatResponse",
    "BuildingCreateRequest",
    "BuildingDetailResponse",
    "BuildingListResponse",
    "BuildingSummaryResponse",
    "ExecutiveReportResponse",
    "ReportCreateRequest",
    "SimulationDetailResponse",
    "SimulationListResponse",
    "SimulationRunRequest",
    "SimulationSummaryResponse",
]
