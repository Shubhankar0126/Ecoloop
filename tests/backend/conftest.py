from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecoloop_backend.infrastructure.config import (
    ApiSettings,
    AppEnvironment,
    AppSettings,
    LoggingSettings,
    Settings,
)
from ecoloop_backend.main import create_app


def build_test_settings() -> Settings:
    """Create a stable settings object for backend tests."""
    return Settings(
        app=AppSettings(
            name="ecoloop-backend-test",
            version="0.1.0-test",
            environment=AppEnvironment.DEVELOPMENT,
        ),
        api=ApiSettings(),
        logging=LoggingSettings(),
    )


def build_test_app(settings: Settings | None = None) -> FastAPI:
    """Create a backend app instance for tests."""
    return create_app(settings or build_test_settings())


def build_test_client(
    app: FastAPI | None = None,
    *,
    settings: Settings | None = None,
    raise_server_exceptions: bool = True,
) -> TestClient:
    """Create a FastAPI test client for the backend app."""
    resolved_app = app or build_test_app(settings)
    return TestClient(resolved_app, raise_server_exceptions=raise_server_exceptions)
