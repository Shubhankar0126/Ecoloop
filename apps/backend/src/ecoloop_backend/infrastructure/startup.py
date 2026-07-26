"""Startup validation utilities for the EcoLoop backend."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ecoloop_backend.infrastructure.config import Settings
from ecoloop_common.exceptions import ConfigurationError

type StartupValidationHandler = Callable[[Settings], None]

_VERSIONED_API_PATH_PATTERN = re.compile(r"^/api/v[1-9][0-9]*$")


@dataclass(frozen=True, slots=True)
class StartupValidation:
    """Named startup validation executed before the application serves requests."""

    name: str
    handler: StartupValidationHandler

    def validate(self, settings: Settings) -> None:
        """Execute the validation against the resolved settings."""
        self.handler(settings)


class StartupValidationRegistry:
    """Ordered registry of startup validations for the backend runtime."""

    def __init__(self, validations: Iterable[StartupValidation]) -> None:
        """Store the validations in the order they should run."""
        self._validations = tuple(validations)

    @property
    def names(self) -> tuple[str, ...]:
        """Return the configured validation names."""
        return tuple(validation.name for validation in self._validations)

    def validate(self, settings: Settings) -> None:
        """Run all registered validations and raise on the first failure."""
        for validation in self._validations:
            try:
                validation.validate(settings)
            except ConfigurationError:
                raise
            except Exception as exc:  # pragma: no cover - defensive wrapping
                raise ConfigurationError(
                    f"Startup validation '{validation.name}' failed.",
                    context={"validation": validation.name},
                ) from exc


def build_startup_validation_registry() -> StartupValidationRegistry:
    """Create the backend's default startup validation registry."""
    return StartupValidationRegistry(
        (
            StartupValidation("app_identity", _validate_app_identity),
            StartupValidation("api_base_path", _validate_api_base_path),
            StartupValidation("logging_configuration", _validate_logging_configuration),
        )
    )


def _validate_app_identity(settings: Settings) -> None:
    """Ensure the service identity fields are suitable for production use."""
    if not settings.app.name.strip():
        raise ConfigurationError(
            "Application name must not be empty.",
            context={"field": "app.name"},
        )

    if not settings.app.version.strip():
        raise ConfigurationError(
            "Application version must not be empty.",
            context={"field": "app.version"},
        )


def _validate_api_base_path(settings: Settings) -> None:
    """Ensure the API base path remains explicitly versioned."""
    if not settings.api.host.strip():
        raise ConfigurationError(
            "API host must not be empty.",
            context={"field": "api.host"},
        )

    if not _VERSIONED_API_PATH_PATTERN.fullmatch(settings.api.base_path):
        raise ConfigurationError(
            "API base path must be versioned and match the pattern '/api/vN'.",
            context={"field": "api.base_path", "value": settings.api.base_path},
        )


def _validate_logging_configuration(settings: Settings) -> None:
    """Ensure structured logging targets are explicitly configured."""
    if not settings.logging.access_logger_name.strip():
        raise ConfigurationError(
            "Access logger name must not be empty.",
            context={"field": "logging.access_logger_name"},
        )

    if not settings.logging.application_logger_name.strip():
        raise ConfigurationError(
            "Application logger name must not be empty.",
            context={"field": "logging.application_logger_name"},
        )

    if settings.logging.access_logger_name == settings.logging.application_logger_name:
        raise ConfigurationError(
            "Access and application logger names must be distinct.",
            context={
                "field": "logging.application_logger_name",
                "value": settings.logging.application_logger_name,
            },
        )
