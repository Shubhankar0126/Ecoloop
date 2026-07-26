"""Application-layer exception types."""

from __future__ import annotations

from ecoloop_common.exceptions.base import EcoLoopError


class ApplicationError(EcoLoopError):
    """Base exception for application service orchestration failures."""

    default_message = "The application could not complete the requested operation."
    error_code = "ecoloop.application_error"
