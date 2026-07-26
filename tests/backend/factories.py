from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from ecoloop_ai import AgentRequest, AgentRunResult, AgentState, OptimizationReport, UserGoal
from ecoloop_ai.memory import AgentMemory
from ecoloop_backend.api.v1.schemas.ai import AiChatResponse
from ecoloop_backend.api.v1.schemas.buildings import BuildingDetailResponse
from ecoloop_backend.api.v1.schemas.reports import ExecutiveReportResponse
from ecoloop_backend.api.v1.schemas.simulations import SimulationDetailResponse
from ecoloop_energyplus import (
    ComfortMetrics,
    EnergyMetrics,
    HVACMetrics,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationStatus,
)

_DEFAULT_DIAGNOSTICS = ("Expected EnergyPlus output artifact was not produced: eplusout.eso.",)


def build_building_detail(
    *,
    building_id: UUID | None = None,
    simulation_count: int = 0,
) -> BuildingDetailResponse:
    resolved_building_id = building_id or uuid4()
    return BuildingDetailResponse(
        building_id=resolved_building_id,
        name="HQ Office Tower",
        description="Primary commercial office baseline for dashboard analytics.",
        timezone="Asia/Kolkata",
        created_at=datetime(2026, 7, 26, 10, 15, tzinfo=UTC),
        simulation_count=simulation_count,
        baseline_idf_path=Path("C:/ecoloop/buildings/hq-office.idf"),
        weather_file_path=Path("C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"),
        metadata={"portfolio": "north-region", "building_type": "office"},
    )


def build_simulation_result(
    *,
    simulation_id: UUID | None = None,
    final_status: SimulationStatus = SimulationStatus.SUCCEEDED,
    diagnostics: tuple[str, ...] = _DEFAULT_DIAGNOSTICS,
) -> SimulationResult:
    resolved_simulation_id = simulation_id or uuid4()
    started_at = datetime(2026, 7, 26, 10, 20, tzinfo=UTC)
    completed_at = datetime(2026, 7, 26, 10, 20, 41, tzinfo=UTC)
    return SimulationResult(
        simulation_id=resolved_simulation_id,
        final_status=final_status,
        metrics=SimulationMetrics(
            energy=EnergyMetrics(
                total_site_energy_kwh=15420.6,
                electricity_consumption_kwh=9630.2,
            ),
            hvac=HVACMetrics(
                heating_energy_kwh=2410.4,
                cooling_energy_kwh=3188.1,
                hvac_energy_kwh=5598.5,
                equipment_loads_kwh=744.0,
            ),
            comfort=ComfortMetrics(
                average_zone_temperature_celsius=23.4,
                average_zone_humidity_percent=48.2,
                average_pmv=0.1,
                average_ppd_percent=9.8,
            ),
        ),
        artifacts=(),
        diagnostics=diagnostics,
        metadata=SimulationMetadata(
            energyplus_version="24.2.0",
            installation_root=Path("C:/EnergyPlusV24-2-0"),
            command_line=("energyplus", "-w", "C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"),
            exit_code=0,
            duration_ms=41234,
            idf_checksum="abc123",
            epw_checksum="def456",
            hostname="ecoloop-runner",
            started_at=started_at,
            completed_at=completed_at,
        ),
    )


def build_simulation_detail(
    *,
    simulation_id: UUID | None = None,
    building_id: UUID | None = None,
    final_status: SimulationStatus = SimulationStatus.SUCCEEDED,
) -> SimulationDetailResponse:
    result = build_simulation_result(
        simulation_id=simulation_id,
        final_status=final_status,
    )
    return SimulationDetailResponse(
        simulation_id=result.simulation_id,
        building_id=building_id,
        final_status=result.final_status,
        created_at=result.metadata.started_at or datetime(2026, 7, 26, 10, 20, tzinfo=UTC),
        idf_path=Path("C:/ecoloop/buildings/hq-office.idf"),
        epw_path=Path("C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"),
        duration_ms=result.metadata.duration_ms,
        energyplus_version=result.metadata.energyplus_version,
        diagnostics_count=len(result.diagnostics),
        result=result,
    )


def build_agent_run_result(
    *,
    latest_simulation_result: SimulationResult | None = None,
) -> AgentRunResult:
    goal = UserGoal(objective="Reduce cooling energy without degrading comfort.")
    request = AgentRequest(goal=goal, max_iterations=3)
    report = OptimizationReport(
        executive_summary="Cooling energy was reduced while preserving comfort.",
        goal_achieved=True,
        iterations_used=2,
        key_findings=("Cooling energy dropped by 6.1%.",),
        recommendations=("Adopt the revised HVAC schedule as the next baseline.",),
        next_actions=("Validate the same schedule under a second weather file.",),
    )
    state = AgentState(
        conversation=request.conversation,
        goal=request.goal,
        simulation_history=(),
        current_plan=None,
        iteration_count=report.iterations_used,
        max_iterations=request.max_iterations or 3,
        latest_simulation_result=latest_simulation_result,
        latest_tool_execution=None,
        latest_analysis=None,
        latest_critique=None,
        messages=(),
        goal_achieved=report.goal_achieved,
        memory=AgentMemory.from_request(request),
        final_report=report,
    )
    return AgentRunResult(final_state=state, report=report)


def build_ai_chat_response(
    *,
    latest_simulation_id: UUID | None = None,
) -> AiChatResponse:
    return AiChatResponse(
        latest_simulation_id=latest_simulation_id,
        report=build_agent_run_result().report,
    )


def build_report_response(
    *,
    simulation_id: UUID | None = None,
    building_id: UUID | None = None,
) -> ExecutiveReportResponse:
    resolved_simulation_id = simulation_id or uuid4()
    return ExecutiveReportResponse(
        simulation_id=resolved_simulation_id,
        building_id=building_id,
        building_name="HQ Office Tower" if building_id is not None else None,
        generated_at=datetime(2026, 7, 26, 10, 30, tzinfo=UTC),
        title="Executive summary for the HQ baseline run",
        executive_summary=(
            "The baseline office simulation completed successfully and produced "
            "normalized energy and comfort metrics for dashboard consumption."
        ),
        final_status=SimulationStatus.SUCCEEDED,
        highlights=(
            "Total site energy: 15420.60 kWh",
            "Electricity consumption: 9630.20 kWh",
        ),
        recommendations=("Use this run as the reference baseline for future comparison reports.",),
        diagnostics=("Expected EnergyPlus output artifact was not produced: eplusout.eso.",),
    )
