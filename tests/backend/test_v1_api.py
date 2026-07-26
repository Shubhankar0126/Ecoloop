from __future__ import annotations

from uuid import uuid4

from tests.backend.conftest import build_test_app, build_test_client
from tests.backend.factories import (
    build_ai_chat_response,
    build_building_detail,
    build_report_response,
    build_simulation_detail,
)

from ecoloop_backend.api.dependencies import (
    get_ai_chat_service,
    get_report_service,
    get_simulation_api_service,
)
from ecoloop_backend.api.v1.schemas.ai import AiChatResponse
from ecoloop_backend.api.v1.schemas.reports import ExecutiveReportResponse
from ecoloop_backend.api.v1.schemas.simulations import (
    SimulationDetailResponse,
    SimulationListResponse,
    SimulationSummaryResponse,
)


class StubSimulationApiService:
    def __init__(self, detail: SimulationDetailResponse) -> None:
        self.detail = detail
        self.last_request: object | None = None

    def run_simulation(self, request: object) -> SimulationDetailResponse:
        self.last_request = request
        return self.detail

    def list_simulations(self) -> SimulationListResponse:
        summary = SimulationSummaryResponse(
            simulation_id=self.detail.simulation_id,
            building_id=self.detail.building_id,
            final_status=self.detail.final_status,
            created_at=self.detail.created_at,
            idf_path=self.detail.idf_path,
            epw_path=self.detail.epw_path,
            duration_ms=self.detail.duration_ms,
            energyplus_version=self.detail.energyplus_version,
            diagnostics_count=self.detail.diagnostics_count,
        )
        return SimulationListResponse(count=1, items=(summary,))

    def get_simulation(self, simulation_id: object) -> SimulationDetailResponse | None:
        if simulation_id == self.detail.simulation_id:
            return self.detail

        return None


class StubAiChatService:
    def __init__(self, response: AiChatResponse) -> None:
        self.response = response
        self.last_request: object | None = None

    def run_chat(self, request: object) -> AiChatResponse:
        self.last_request = request
        return self.response


class StubReportService:
    def __init__(self, response: ExecutiveReportResponse | None) -> None:
        self.response = response
        self.last_request: object | None = None

    def generate_report(self, request: object) -> ExecutiveReportResponse | None:
        self.last_request = request
        return self.response


def test_openapi_includes_required_backend_paths() -> None:
    with build_test_client() as client:
        response = client.get("/api/v1/openapi.json")

    payload = response.json()

    assert response.status_code == 200
    assert "/api/v1/buildings" in payload["paths"]
    assert "/api/v1/buildings/{building_id}" in payload["paths"]
    assert "/api/v1/simulations" in payload["paths"]
    assert "/api/v1/simulations/{simulation_id}" in payload["paths"]
    assert "/api/v1/ai/chat" in payload["paths"]
    assert "/api/v1/reports" in payload["paths"]
    assert "/api/v1/health/live" in payload["paths"]


def test_building_endpoints_create_list_and_get_resources() -> None:
    with build_test_client() as client:
        create_response = client.post(
            "/api/v1/buildings",
            json={
                "name": "HQ Office Tower",
                "description": "Primary commercial office baseline for dashboard analytics.",
                "timezone": "Asia/Kolkata",
                "baseline_idf_path": "C:/ecoloop/buildings/hq-office.idf",
                "weather_file_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
                "metadata": {"portfolio": "north-region"},
            },
        )
        building_id = create_response.json()["building_id"]
        list_response = client.get("/api/v1/buildings")
        detail_response = client.get(f"/api/v1/buildings/{building_id}")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["building_id"] == building_id


def test_building_detail_returns_problem_details_when_missing() -> None:
    with build_test_client() as client:
        response = client.get(f"/api/v1/buildings/{uuid4()}")

    payload = response.json()

    assert response.status_code == 404
    assert payload["title"] == "Not Found"
    assert payload["detail"] == "Building not found."


def test_simulation_endpoints_use_dependency_overrides() -> None:
    app = build_test_app()
    detail = build_simulation_detail(building_id=uuid4())
    stub_service = StubSimulationApiService(detail)
    app.dependency_overrides[get_simulation_api_service] = lambda: stub_service

    with build_test_client(app) as client:
        create_response = client.post(
            "/api/v1/simulations",
            json={
                "building_id": str(detail.building_id),
                "idf_path": "C:/ecoloop/buildings/hq-office.idf",
                "epw_path": "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw",
                "timeout_seconds": 1800,
                "parallel_jobs": 1,
            },
        )
        list_response = client.get("/api/v1/simulations")
        detail_response = client.get(f"/api/v1/simulations/{detail.simulation_id}")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["simulation_id"] == str(detail.simulation_id)
    assert stub_service.last_request is not None


def test_simulation_detail_returns_problem_details_when_missing() -> None:
    app = build_test_app()
    stub_service = StubSimulationApiService(build_simulation_detail())
    app.dependency_overrides[get_simulation_api_service] = lambda: stub_service

    with build_test_client(app) as client:
        response = client.get(f"/api/v1/simulations/{uuid4()}")

    payload = response.json()

    assert response.status_code == 404
    assert payload["title"] == "Not Found"
    assert payload["detail"] == "Simulation not found."


def test_ai_chat_endpoint_uses_dependency_override() -> None:
    app = build_test_app()
    response_model = build_ai_chat_response(latest_simulation_id=uuid4())
    stub_service = StubAiChatService(response_model)
    app.dependency_overrides[get_ai_chat_service] = lambda: stub_service

    with build_test_client(app) as client:
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "goal": {"objective": "Reduce cooling energy without degrading comfort."},
                "conversation": [],
                "previous_optimizations": [],
                "max_iterations": 3,
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["report"]["goal_achieved"] is True
    assert stub_service.last_request is not None


def test_report_endpoint_uses_dependency_override() -> None:
    app = build_test_app()
    building = build_building_detail()
    report = build_report_response(building_id=building.building_id)
    stub_service = StubReportService(report)
    app.dependency_overrides[get_report_service] = lambda: stub_service

    with build_test_client(app) as client:
        response = client.post(
            "/api/v1/reports",
            json={"simulation_id": str(report.simulation_id), "include_diagnostics": True},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["simulation_id"] == str(report.simulation_id)
    assert stub_service.last_request is not None


def test_report_endpoint_returns_problem_details_when_missing() -> None:
    app = build_test_app()
    app.dependency_overrides[get_report_service] = lambda: StubReportService(None)

    with build_test_client(app) as client:
        response = client.post(
            "/api/v1/reports",
            json={"simulation_id": str(uuid4()), "include_diagnostics": True},
        )

    payload = response.json()

    assert response.status_code == 404
    assert payload["title"] == "Not Found"
    assert payload["detail"] == "Simulation not found."
