from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient
from tests.backend.conftest import build_test_app, build_test_client

from ecoloop_common.exceptions import (
    ApplicationError,
    DomainError,
    InfrastructureError,
    ValidationError,
)


def build_exception_test_app() -> APIRouter:
    """Create a test router that raises different application exceptions."""
    router = APIRouter(prefix="/test")

    @router.get("/domain-error")
    def domain_error() -> dict[str, str]:
        raise DomainError("Building state transition is invalid.", context={"building_id": "b-001"})

    @router.get("/validation-error")
    def validation_error() -> dict[str, str]:
        raise ValidationError("Setpoint must be between 18 and 30.")

    @router.get("/application-error")
    def application_error() -> dict[str, str]:
        raise ApplicationError("Unable to complete the orchestration step.")

    @router.get("/infrastructure-error")
    def infrastructure_error() -> dict[str, str]:
        raise InfrastructureError("Redis is unavailable.")

    @router.get("/unexpected-error")
    def unexpected_error() -> dict[str, str]:
        raise RuntimeError("sensitive runtime detail")

    @router.get("/request-validation")
    def request_validation(value: int) -> dict[str, int]:
        return {"value": value}

    return router


def test_domain_error_returns_rfc_7807_problem_details() -> None:
    app = build_test_app()
    app.include_router(build_exception_test_app(), prefix="/api/v1")

    with build_test_client(app) as client:
        response = client.get("/api/v1/test/domain-error")

    payload = response.json()
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Request-ID"]
    assert payload["type"] == "urn:ecoloop:problem:ecoloop:domain-error"
    assert payload["title"] == "Domain rule violated"
    assert payload["status"] == 409
    assert payload["detail"] == "Building state transition is invalid."
    assert payload["instance"] == "/api/v1/test/domain-error"
    assert payload["error_code"] == "ecoloop.domain_error"
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["context"] == {"building_id": "b-001"}


def test_request_validation_returns_problem_details_extensions() -> None:
    app = build_test_app()
    app.include_router(build_exception_test_app(), prefix="/api/v1")

    with build_test_client(app) as client:
        response = client.get("/api/v1/test/request-validation", params={"value": "invalid"})

    payload = response.json()
    assert response.status_code == 422
    assert payload["type"] == "urn:ecoloop:problem:request-validation"
    assert payload["title"] == "Request validation failed"
    assert payload["error_code"] == "http.request_validation"
    assert payload["errors"]
    assert payload["errors"][0]["name"] == "value"
    assert payload["errors"][0]["location"] == "query.value"


def test_domain_validation_error_returns_bad_request_problem_details() -> None:
    app = build_test_app()
    app.include_router(build_exception_test_app(), prefix="/api/v1")

    with build_test_client(app) as client:
        response = client.get("/api/v1/test/validation-error")

    payload = response.json()
    assert response.status_code == 400
    assert payload["title"] == "Domain validation failed"
    assert payload["error_code"] == "ecoloop.validation_error"


def test_application_and_infrastructure_errors_map_to_server_problem_details() -> None:
    app = build_test_app()
    app.include_router(build_exception_test_app(), prefix="/api/v1")

    with build_test_client(app) as client:
        application_response = client.get("/api/v1/test/application-error")
        infrastructure_response = client.get("/api/v1/test/infrastructure-error")

    assert application_response.status_code == 500
    assert application_response.json()["title"] == "Application operation failed"
    assert infrastructure_response.status_code == 503
    assert infrastructure_response.json()["title"] == "Infrastructure dependency failed"


def test_unexpected_error_hides_internal_details() -> None:
    app = build_test_app()
    app.include_router(build_exception_test_app(), prefix="/api/v1")

    with build_test_client(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test/unexpected-error")

    payload = response.json()
    assert response.status_code == 500
    assert payload["title"] == "Unexpected application error"
    assert payload["detail"] == "An unexpected error occurred."
    assert "sensitive runtime detail" not in payload["detail"]


def test_not_found_returns_http_problem_details() -> None:
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/does-not-exist")

    payload = response.json()
    assert response.status_code == 404
    assert payload["type"] == "about:blank"
    assert payload["title"] == "Not Found"
    assert payload["status"] == 404


def test_missing_container_returns_problem_details() -> None:
    app = build_test_app()
    delattr(app.state, "container")

    with build_test_client(app) as client:
        response = client.get("/api/v1/health/live")

    payload = response.json()
    assert response.status_code == 503
    assert payload["title"] == "Infrastructure dependency failed"
    assert payload["error_code"] == "ecoloop.infrastructure_error"
