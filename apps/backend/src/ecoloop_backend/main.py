from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from ecoloop_backend.api.exception_handlers import register_exception_handlers
from ecoloop_backend.api.middleware import RequestContextMiddleware
from ecoloop_backend.api.v1.router import router as api_v1_router
from ecoloop_backend.infrastructure.config import Settings, load_settings
from ecoloop_backend.infrastructure.container import build_container
from ecoloop_backend.infrastructure.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings)
    container = build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            container.app_logger.info(
                "Application startup initiated",
                extra={
                    "event": "application_startup_initiated",
                    "service": resolved_settings.app.name,
                    "environment": resolved_settings.app.environment.value,
                },
            )
            container.startup_validators.validate(resolved_settings)
            container.app_logger.info(
                "Application services registered",
                extra={
                    "event": "application_services_registered",
                    "service": resolved_settings.app.name,
                    "services": list(container.service_names),
                    "startup_validations": list(container.startup_validators.names),
                },
            )
            container.app_logger.info(
                "Application startup completed",
                extra={
                    "event": "application_startup_completed",
                    "service": resolved_settings.app.name,
                    "environment": resolved_settings.app.environment.value,
                },
            )
        except Exception:
            await container.shutdown()
            logging.shutdown()
            raise

        yield
        try:
            container.app_logger.info(
                "Application shutdown initiated",
                extra={
                    "event": "application_shutdown_initiated",
                    "service": resolved_settings.app.name,
                    "environment": resolved_settings.app.environment.value,
                },
            )
            await container.shutdown()
            container.app_logger.info(
                "Application shutdown completed",
                extra={
                    "event": "application_shutdown_completed",
                    "service": resolved_settings.app.name,
                    "environment": resolved_settings.app.environment.value,
                },
            )
        finally:
            logging.shutdown()

    app = FastAPI(
        title=resolved_settings.app.name,
        version=resolved_settings.app.version,
        debug=resolved_settings.app.debug,
        openapi_url=f"{resolved_settings.api.base_path}/openapi.json",
        docs_url=f"{resolved_settings.api.base_path}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.container = container
    register_exception_handlers(app)
    app.add_middleware(
        RequestContextMiddleware,
        logger_name=resolved_settings.logging.access_logger_name,
    )
    app.include_router(api_v1_router, prefix=resolved_settings.api.base_path)
    return app


def run() -> None:
    settings = load_settings()
    uvicorn.run(
        "ecoloop_backend.main:create_app",
        factory=True,
        host=settings.api.host,
        port=settings.api.port,
        access_log=False,
        log_config=None,
    )
