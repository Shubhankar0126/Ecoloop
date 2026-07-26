from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ecoloop_ai import EcoLoopAgent, InProcessMcpToolClient
from ecoloop_backend.api.v1.services import (
    AiChatService,
    BackendRuntimeState,
    BuildingCatalogService,
    ExecutiveReportService,
    SimulationApiService,
)
from ecoloop_backend.application.services.health_service import HealthService
from ecoloop_backend.infrastructure.config import Settings
from ecoloop_backend.infrastructure.startup import (
    StartupValidationRegistry,
    build_startup_validation_registry,
)
from ecoloop_energyplus import InputValidator, SimulationService
from ecoloop_mcp import McpServerDependencies, create_mcp_server

type ShutdownCallback = Callable[[], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Container for runtime dependencies and lifecycle hooks."""

    settings: Settings
    health_service: HealthService
    building_service: BuildingCatalogService
    simulation_api_service: SimulationApiService
    ai_chat_service: AiChatService
    report_service: ExecutiveReportService
    app_logger: logging.Logger
    service_names: tuple[str, ...]
    startup_validators: StartupValidationRegistry
    shutdown_callbacks: tuple[ShutdownCallback, ...]

    async def shutdown(self) -> None:
        """Run registered shutdown callbacks in order."""
        for callback in self.shutdown_callbacks:
            result = callback()
            if inspect.isawaitable(result):
                await result


def build_container(settings: Settings) -> ApplicationContainer:
    """Build the backend dependency container from the resolved settings."""
    app_logger = logging.getLogger(settings.logging.application_logger_name)
    health_service = HealthService(
        service_name=settings.app.name,
        environment=settings.app.environment.value,
        version=settings.app.version,
        logger=app_logger.getChild("health"),
    )
    simulation_service = SimulationService(settings.energyplus_platform)
    mcp_server_dependencies = McpServerDependencies(
        simulation_service=simulation_service,
        input_validator=InputValidator(),
        simulation_settings=settings.energyplus_platform.simulation,
    )
    ai_agent = EcoLoopAgent.from_dependencies(
        config=settings.ai_agent,
        tool_client=InProcessMcpToolClient(create_mcp_server(mcp_server_dependencies)),
    )
    runtime_state = BackendRuntimeState()
    building_service = BuildingCatalogService(
        state=runtime_state,
        logger=app_logger.getChild("buildings"),
    )
    simulation_api_service = SimulationApiService(
        state=runtime_state,
        simulation_service=simulation_service,
        logger=app_logger.getChild("simulations"),
    )
    ai_chat_service = AiChatService(
        agent=ai_agent,
        logger=app_logger.getChild("ai"),
    )
    report_service = ExecutiveReportService(
        state=runtime_state,
        logger=app_logger.getChild("reports"),
    )
    return ApplicationContainer(
        settings=settings,
        health_service=health_service,
        building_service=building_service,
        simulation_api_service=simulation_api_service,
        ai_chat_service=ai_chat_service,
        report_service=report_service,
        app_logger=app_logger,
        service_names=(
            "health_service",
            "building_service",
            "simulation_api_service",
            "ai_chat_service",
            "report_service",
        ),
        startup_validators=build_startup_validation_registry(),
        shutdown_callbacks=(),
    )
