from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from tests.backend.factories import (
    build_agent_run_result,
    build_building_detail,
    build_simulation_detail,
    build_simulation_result,
)

from ecoloop_ai import UserGoal
from ecoloop_backend.api.v1.schemas.ai import AiChatRequest
from ecoloop_backend.api.v1.schemas.buildings import BuildingCreateRequest
from ecoloop_backend.api.v1.schemas.reports import ReportCreateRequest
from ecoloop_backend.api.v1.schemas.simulations import SimulationRunRequest
from ecoloop_backend.api.v1.services import (
    AiChatService,
    BackendRuntimeState,
    BuildingCatalogService,
    ExecutiveReportService,
    SimulationApiService,
)
from ecoloop_common.exceptions import ValidationError
from ecoloop_energyplus import SimulationResult


class FakeSimulationPlatformService:
    def __init__(self) -> None:
        self.last_request: object | None = None
        self.result = build_simulation_result()

    def run(self, spec: object) -> SimulationResult:
        self.last_request = spec
        return self.result


class FakeAgent:
    def __init__(self, *, latest_simulation_id: UUID | None = None) -> None:
        latest_result = None
        if latest_simulation_id is not None:
            latest_result = build_simulation_result(simulation_id=latest_simulation_id)
        self.last_request: object | None = None
        self.result = build_agent_run_result(latest_simulation_result=latest_result)

    def run(self, request: object) -> object:
        self.last_request = request
        return self.result


def test_building_catalog_service_tracks_created_buildings_and_simulation_counts() -> None:
    state = BackendRuntimeState()
    service = BuildingCatalogService(
        state=state,
        logger=logging.getLogger("tests.buildings"),
    )
    building = service.create_building(
        BuildingCreateRequest(
            name="HQ Office Tower",
            description="Primary commercial office baseline for dashboard analytics.",
            timezone="Asia/Kolkata",
        )
    )
    state.simulations[uuid4()] = build_simulation_detail(building_id=building.building_id)

    collection = service.list_buildings()
    detail = service.get_building(building.building_id)

    assert collection.count == 1
    assert collection.items[0].simulation_count == 1
    assert detail is not None
    assert detail.simulation_count == 1
    assert service.exists(building.building_id) is True
    assert service.get_building_name(building.building_id) == building.name


def test_simulation_api_service_runs_and_records_history() -> None:
    state = BackendRuntimeState()
    building = build_building_detail()
    state.buildings[building.building_id] = building
    platform_service = FakeSimulationPlatformService()
    service = SimulationApiService(
        state=state,
        simulation_service=platform_service,  # type: ignore[arg-type]
        logger=logging.getLogger("tests.simulations"),
    )
    assert building.baseline_idf_path is not None
    assert building.weather_file_path is not None

    detail = service.run_simulation(
        SimulationRunRequest(
            building_id=building.building_id,
            idf_path=building.baseline_idf_path,
            epw_path=building.weather_file_path,
            timeout_seconds=1800,
            parallel_jobs=1,
        )
    )
    history = service.list_simulations()

    assert detail.simulation_id == platform_service.result.simulation_id
    assert history.count == 1
    assert history.items[0].simulation_id == detail.simulation_id
    assert service.get_simulation(detail.simulation_id) == detail
    assert platform_service.last_request is not None


def test_simulation_api_service_rejects_unknown_building() -> None:
    service = SimulationApiService(
        state=BackendRuntimeState(),
        simulation_service=FakeSimulationPlatformService(),  # type: ignore[arg-type]
        logger=logging.getLogger("tests.simulations"),
    )

    with pytest.raises(ValidationError, match="building_id"):
        service.run_simulation(
            SimulationRunRequest(
                building_id=uuid4(),
                idf_path=Path("C:/ecoloop/buildings/hq-office.idf"),
                epw_path=Path("C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"),
            )
        )


def test_ai_chat_service_returns_normalized_response() -> None:
    latest_simulation_id = uuid4()
    agent = FakeAgent(latest_simulation_id=latest_simulation_id)
    service = AiChatService(
        agent=agent,  # type: ignore[arg-type]
        logger=logging.getLogger("tests.ai"),
    )

    response = service.run_chat(
        AiChatRequest(
            goal=UserGoal(objective="Reduce cooling energy without degrading comfort."),
            max_iterations=3,
        )
    )

    assert response.latest_simulation_id == latest_simulation_id
    assert response.report.goal_achieved is True
    assert agent.last_request is not None


def test_executive_report_service_generates_deterministic_report() -> None:
    state = BackendRuntimeState()
    building = build_building_detail()
    simulation = build_simulation_detail(building_id=building.building_id)
    state.buildings[building.building_id] = building
    state.simulations[simulation.simulation_id] = simulation
    service = ExecutiveReportService(
        state=state,
        logger=logging.getLogger("tests.reports"),
    )

    report = service.generate_report(
        ReportCreateRequest(
            simulation_id=simulation.simulation_id,
            include_diagnostics=False,
        )
    )

    assert report is not None
    assert report.building_name == building.name
    assert report.diagnostics == ()
    assert report.highlights
    assert report.recommendations


def test_executive_report_service_returns_none_for_missing_simulation() -> None:
    service = ExecutiveReportService(
        state=BackendRuntimeState(),
        logger=logging.getLogger("tests.reports"),
    )

    report = service.generate_report(ReportCreateRequest(simulation_id=uuid4()))

    assert report is None
