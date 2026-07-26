"""Infrastructure-level exception types."""

from __future__ import annotations

from ecoloop_common.exceptions.base import EcoLoopError


class InfrastructureError(EcoLoopError):
    """Base exception for failures in external systems or platform resources."""

    default_message = "An infrastructure dependency failed."
    error_code = "ecoloop.infrastructure_error"


class ConfigurationError(InfrastructureError):
    """Raised when application configuration is missing or invalid."""

    default_message = "Application configuration is invalid."
    error_code = "ecoloop.configuration_error"
