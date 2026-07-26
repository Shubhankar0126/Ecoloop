from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ecoloop_backend.api.v1.services import (
    AiChatService,
    BuildingCatalogService,
    ExecutiveReportService,
    SimulationApiService,
)
from ecoloop_backend.application.services.health_service import HealthService
from ecoloop_backend.infrastructure.container import ApplicationContainer
from ecoloop_common.exceptions import InfrastructureError


def get_container(request: Request) -> ApplicationContainer:
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, ApplicationContainer):
        raise InfrastructureError(
            "Application container is not configured.",
            context={"component": "application_container"},
        )

    return container


def get_health_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> HealthService:
    """Resolve the health service from the application container."""
    return container.health_service


def get_building_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> BuildingCatalogService:
    """Resolve the building catalog service from the application container."""
    return container.building_service


def get_simulation_api_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SimulationApiService:
    """Resolve the simulation API service from the application container."""
    return container.simulation_api_service


def get_ai_chat_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AiChatService:
    """Resolve the AI chat service from the application container."""
    return container.ai_chat_service


def get_report_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ExecutiveReportService:
    """Resolve the executive report service from the application container."""
    return container.report_service
