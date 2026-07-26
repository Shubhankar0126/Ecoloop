from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from tests.backend.conftest import build_test_app, build_test_settings

from ecoloop_backend.application.services.health_service import HealthService
from ecoloop_backend.infrastructure.config import LoggingSettings
from ecoloop_backend.infrastructure.container import ApplicationContainer
from ecoloop_backend.infrastructure.startup import build_startup_validation_registry
from ecoloop_common.exceptions import ConfigurationError


def test_startup_validation_registry_exposes_expected_validations() -> None:
    registry = build_startup_validation_registry()

    assert registry.names == (
        "app_identity",
        "api_base_path",
        "logging_configuration",
    )


def test_startup_validation_registry_rejects_invalid_api_base_path() -> None:
    settings = build_test_settings()
    settings = settings.model_copy(
        update={"api": settings.api.model_copy(update={"base_path": "/api"})}
    )

    with pytest.raises(ConfigurationError, match="API base path must be versioned"):
        build_startup_validation_registry().validate(settings)


def test_startup_validation_registry_rejects_empty_service_identity() -> None:
    settings = build_test_settings().model_copy(
        update={"app": build_test_settings().app.model_copy(update={"name": ""})}
    )

    with pytest.raises(ConfigurationError, match="Application name must not be empty"):
        build_startup_validation_registry().validate(settings)


def test_startup_validation_registry_rejects_empty_host() -> None:
    settings = build_test_settings().model_copy(
        update={"api": build_test_settings().api.model_copy(update={"host": ""})}
    )

    with pytest.raises(ConfigurationError, match="API host must not be empty"):
        build_startup_validation_registry().validate(settings)


def test_application_startup_fails_for_invalid_logging_configuration() -> None:
    settings = build_test_settings().model_copy(
        update={
            "logging": LoggingSettings(
                access_logger_name="ecoloop.shared",
                application_logger_name="ecoloop.shared",
            )
        }
    )
    app = build_test_app(settings)

    with pytest.raises(ConfigurationError, match="must be distinct"), TestClient(app):
        pass


def test_application_startup_succeeds_for_valid_settings() -> None:
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200


def test_container_shutdown_runs_registered_callbacks() -> None:
    events: list[str] = []

    def sync_shutdown_callback() -> None:
        events.append("sync")

    async def async_shutdown_callback() -> None:
        events.append("async")

    settings = build_test_settings()
    container = ApplicationContainer(
        settings=settings,
        health_service=HealthService(
            service_name=settings.app.name,
            environment=settings.app.environment.value,
            version=settings.app.version,
            logger=logging.getLogger("test.health"),
        ),
        building_service=cast(Any, object()),
        simulation_api_service=cast(Any, object()),
        ai_chat_service=cast(Any, object()),
        report_service=cast(Any, object()),
        app_logger=logging.getLogger("test.app"),
        service_names=(
            "health_service",
            "building_service",
            "simulation_api_service",
            "ai_chat_service",
            "report_service",
        ),
        startup_validators=build_startup_validation_registry(),
        shutdown_callbacks=(sync_shutdown_callback, async_shutdown_callback),
    )

    asyncio.run(container.shutdown())

    assert events == ["sync", "async"]
