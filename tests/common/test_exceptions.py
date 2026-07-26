from __future__ import annotations

from types import MappingProxyType

import pytest

from ecoloop_common.exceptions import (
    ApplicationError,
    ConfigurationError,
    DomainError,
    EcoLoopError,
    InfrastructureError,
    UnexpectedError,
    ValidationError,
)


def test_ecoloop_error_exposes_message_context_and_error_code() -> None:
    error = EcoLoopError("Foundation failure", context={"service": "backend"})

    assert str(error) == "Foundation failure"
    assert error.message == "Foundation failure"
    assert error.context == MappingProxyType({"service": "backend"})
    assert error.as_dict() == {
        "type": "EcoLoopError",
        "message": "Foundation failure",
        "error_code": "ecoloop.error",
        "context": {"service": "backend"},
    }


def test_ecoloop_error_context_is_immutable() -> None:
    error = EcoLoopError(context={"service": "backend"})

    with pytest.raises(TypeError):
        error.context["service"] = "worker"  # type: ignore[index]


def test_exception_hierarchy_is_consistent() -> None:
    assert issubclass(DomainError, EcoLoopError)
    assert issubclass(ValidationError, DomainError)
    assert issubclass(ApplicationError, EcoLoopError)
    assert issubclass(InfrastructureError, EcoLoopError)
    assert issubclass(ConfigurationError, InfrastructureError)
    assert issubclass(UnexpectedError, EcoLoopError)
