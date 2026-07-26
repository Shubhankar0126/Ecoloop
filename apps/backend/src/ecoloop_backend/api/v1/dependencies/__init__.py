"""Versioned dependency providers for backend API routers."""

from ecoloop_backend.api.dependencies import (
    get_ai_chat_service,
    get_building_service,
    get_container,
    get_health_service,
    get_report_service,
    get_simulation_api_service,
)

__all__ = [
    "get_ai_chat_service",
    "get_building_service",
    "get_container",
    "get_health_service",
    "get_report_service",
    "get_simulation_api_service",
]
