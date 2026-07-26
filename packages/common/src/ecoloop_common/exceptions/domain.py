"""Domain-level exception types."""

from __future__ import annotations

from ecoloop_common.exceptions.base import EcoLoopError


class DomainError(EcoLoopError):
    """Base exception for domain invariants and business rule violations."""

    default_message = "A domain rule was violated."
    error_code = "ecoloop.domain_error"


class ValidationError(DomainError):
    """Raised when a domain value or invariant fails validation."""

    default_message = "Domain validation failed."
    error_code = "ecoloop.validation_error"
