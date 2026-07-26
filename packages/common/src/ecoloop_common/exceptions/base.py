"""Base exception types shared across EcoLoop AI services."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar


class EcoLoopError(Exception):
    """Base class for all framework-independent EcoLoop exceptions."""

    default_message: ClassVar[str] = "EcoLoop operation failed."
    error_code: ClassVar[str] = "ecoloop.error"

    def __init__(
        self,
        message: str | None = None,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize the exception with an optional message and structured context."""
        self.message = message or self.default_message
        self.context = MappingProxyType(dict(context or {}))
        super().__init__(self.message)

    def as_dict(self) -> dict[str, object]:
        """Return a generic serialized representation of the exception."""
        return {
            "type": type(self).__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": dict(self.context),
        }


class UnexpectedError(EcoLoopError):
    """Fallback error used when no more specific exception type fits."""

    default_message = "An unexpected error occurred."
    error_code = "ecoloop.unexpected_error"
