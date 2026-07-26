"""FastAPI exception handlers for RFC 7807-compatible error responses."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ecoloop_backend.api.error_models import (
    PROBLEM_JSON_MEDIA_TYPE,
    InvalidParameter,
    ProblemDetails,
)
from ecoloop_backend.infrastructure.container import ApplicationContainer
from ecoloop_backend.infrastructure.request_context import get_request_id
from ecoloop_common.exceptions import (
    ApplicationError,
    ConfigurationError,
    DomainError,
    EcoLoopError,
    InfrastructureError,
    UnexpectedError,
)
from ecoloop_common.exceptions import (
    ValidationError as DomainValidationError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register the backend's HTTP exception handlers."""
    app.add_exception_handler(EcoLoopError, cast(Any, handle_ecoloop_error))
    app.add_exception_handler(
        RequestValidationError,
        cast(Any, handle_request_validation_error),
    )
    app.add_exception_handler(StarletteHTTPException, cast(Any, handle_http_exception))
    app.add_exception_handler(Exception, cast(Any, handle_unexpected_exception))


async def handle_ecoloop_error(request: Request, exc: EcoLoopError) -> JSONResponse:
    """Render EcoLoop domain and infrastructure exceptions as RFC 7807 responses."""
    status_code, title = _classify_ecoloop_error(exc)
    problem = ProblemDetails(
        type=_problem_type(exc.error_code),
        title=title,
        status=status_code,
        detail=exc.message,
        instance=request.url.path,
        error_code=exc.error_code,
        request_id=get_request_id(),
        context=dict(exc.context) or None,
    )
    _log_handled_exception(request, exc, status_code)
    return _problem_response(problem)


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Render FastAPI request validation errors as RFC 7807 responses."""
    problem = ProblemDetails(
        type="urn:ecoloop:problem:request-validation",
        title="Request validation failed",
        status=422,
        detail="The request payload or parameters were invalid.",
        instance=request.url.path,
        error_code="http.request_validation",
        request_id=get_request_id(),
        errors=_build_invalid_parameters(exc),
    )
    _get_application_logger(request).warning(
        "Request validation failed",
        extra={
            "event": "http_request_validation_failed",
            "request_id": get_request_id(),
            "path": request.url.path,
            "method": request.method,
            "errors": [error.model_dump() for error in problem.errors or []],
        },
    )
    return _problem_response(problem)


async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Render framework HTTP exceptions as RFC 7807 responses."""
    title = HTTPStatus(exc.status_code).phrase
    detail = str(exc.detail) if exc.detail else title
    problem = ProblemDetails(
        type="about:blank",
        title=title,
        status=exc.status_code,
        detail=detail,
        instance=request.url.path,
        request_id=get_request_id(),
    )
    _log_http_exception(request, exc.status_code)
    return _problem_response(problem)


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Render unexpected server errors as RFC 7807 responses."""
    logger = _get_application_logger(request)
    logger.exception(
        "Unhandled exception",
        extra={
            "event": "http_request_unexpected_error",
            "request_id": get_request_id(),
            "path": request.url.path,
            "method": request.method,
        },
    )
    unexpected_error = UnexpectedError()
    problem = ProblemDetails(
        type=_problem_type(unexpected_error.error_code),
        title="Unexpected application error",
        status=500,
        detail=unexpected_error.message,
        instance=request.url.path,
        error_code=unexpected_error.error_code,
        request_id=get_request_id(),
    )
    return _problem_response(problem)


def _classify_ecoloop_error(exc: EcoLoopError) -> tuple[int, str]:
    """Map a framework-independent EcoLoop exception to an HTTP status and title."""
    if isinstance(exc, DomainValidationError):
        return 400, "Domain validation failed"
    if isinstance(exc, ConfigurationError):
        return 500, "Application configuration is invalid"
    if isinstance(exc, InfrastructureError):
        return 503, "Infrastructure dependency failed"
    if isinstance(exc, ApplicationError):
        return 500, "Application operation failed"
    if isinstance(exc, DomainError):
        return 409, "Domain rule violated"
    return 500, "EcoLoop operation failed"


def _problem_type(error_code: str) -> str:
    """Return a stable URI-like problem type for an EcoLoop error code."""
    normalized_error_code = error_code.replace(".", ":").replace("_", "-")
    return f"urn:ecoloop:problem:{normalized_error_code}"


def _problem_response(problem: ProblemDetails) -> JSONResponse:
    """Serialize a problem details model as an RFC 7807 response."""
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


def _build_invalid_parameters(exc: RequestValidationError) -> list[InvalidParameter]:
    """Transform FastAPI validation issues into a stable error extension payload."""
    errors: list[InvalidParameter] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        name = str(error["loc"][-1]) if error["loc"] else "request"
        errors.append(
            InvalidParameter(
                name=name,
                location=location,
                message=error["msg"],
            )
        )

    return errors


def _log_handled_exception(request: Request, exc: EcoLoopError, status_code: int) -> None:
    """Write a structured log entry for a handled EcoLoop exception."""
    logger = _get_application_logger(request)
    log_method = logger.warning if status_code < 500 else logger.error
    log_method(
        "Handled application exception",
        extra={
            "event": "http_request_handled_exception",
            "request_id": get_request_id(),
            "path": request.url.path,
            "method": request.method,
            "status_code": status_code,
            "error_code": exc.error_code,
            "exception_type": type(exc).__name__,
            "context": dict(exc.context),
        },
    )


def _log_http_exception(request: Request, status_code: int) -> None:
    """Write a structured log entry for a handled HTTP exception."""
    logger = _get_application_logger(request)
    log_method = logger.info if status_code < 500 else logger.error
    log_method(
        "Handled HTTP exception",
        extra={
            "event": "http_request_handled_http_exception",
            "request_id": get_request_id(),
            "path": request.url.path,
            "method": request.method,
            "status_code": status_code,
        },
    )


def _get_application_logger(request: Request) -> logging.Logger:
    """Resolve the configured application logger from app state when available."""
    container = getattr(request.app.state, "container", None)
    if isinstance(container, ApplicationContainer):
        return container.app_logger

    return logging.getLogger("ecoloop.application")
