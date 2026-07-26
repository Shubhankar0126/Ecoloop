from __future__ import annotations

from tests.backend.conftest import build_test_client


def test_liveness_endpoint_returns_expected_payload() -> None:
    with build_test_client() as client:
        response = client.get("/api/v1/health/live")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "ecoloop-backend-test"
    assert payload["environment"] == "development"
    assert payload["version"] == "0.1.0-test"
    assert payload["checked_at"]
    assert response.headers["X-Request-ID"]


def test_readiness_endpoint_returns_expected_payload() -> None:
    with build_test_client() as client:
        response = client.get("/api/v1/health/ready")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "ecoloop-backend-test"


def test_request_id_header_is_preserved_when_supplied() -> None:
    request_id = "architect-review-001"

    with build_test_client() as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": request_id},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
