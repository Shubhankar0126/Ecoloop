"""Framework-independent exception hierarchy for EcoLoop AI."""

from ecoloop_common.exceptions.application import ApplicationError
from ecoloop_common.exceptions.base import EcoLoopError, UnexpectedError
from ecoloop_common.exceptions.domain import DomainError, ValidationError
from ecoloop_common.exceptions.infrastructure import ConfigurationError, InfrastructureError

__all__ = [
    "ApplicationError",
    "ConfigurationError",
    "DomainError",
    "EcoLoopError",
    "InfrastructureError",
    "UnexpectedError",
    "ValidationError",
]
