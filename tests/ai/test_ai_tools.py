from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from ecoloop_ai import AgentToolName, InProcessMcpToolClient, ToolExecutionRecord, parse_tool_output
from ecoloop_energyplus import (
    EnergyMetrics,
    InputValidator,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationService,
    SimulationSettings,
    SimulationStatus,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from ecoloop_energyplus.domain.exceptions import SimulationError
from ecoloop_mcp import McpServerDependencies, create_mcp_server


class StubSimulationService:
    """Simulation service stub used to build an in-process MCP server."""

    def __init__(
        self,
        *,
        result: SimulationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error

    def run(self, spec: object) -> SimulationResult:
        del spec
        if self._error is not None:
            raise self._error

        assert self._result is not None
        return self._result


class StubInputValidator:
    """Validation stub used by the MCP validation tool."""

    def __init__(self, result: ValidationResult) -> None:
        self._result = result

    def validate(self, spec: object, settings: SimulationSettings) -> ValidationResult:
        del spec, settings
        return self._result


def _result(identifier: str) -> SimulationResult:
    return SimulationResult(
        simulation_id=UUID(identifier),
        final_status=SimulationStatus.SUCCEEDED,
        metrics=SimulationMetrics(
            energy=EnergyMetrics(
                total_site_energy_kwh=850.0,
                electricity_consumption_kwh=470.0,
            )
        ),
        diagnostics=("Simulation completed.",),
        metadata=SimulationMetadata(
            energyplus_version="25.1.0",
            command_line=("energyplus",),
            exit_code=0,
            duration_ms=400,
            started_at=datetime(2026, 7, 26, 8, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 26, 8, 1, tzinfo=UTC),
        ),
    )


def _dependencies(
    *,
    result: SimulationResult | None = None,
    error: Exception | None = None,
    validation_result: ValidationResult | None = None,
) -> McpServerDependencies:
    return McpServerDependencies(
        simulation_service=cast(
            SimulationService,
            StubSimulationService(result=result, error=error),
        ),
        input_validator=cast(
            InputValidator,
            StubInputValidator(validation_result or ValidationResult.success()),
        ),
        simulation_settings=SimulationSettings(
            default_timeout_seconds=60,
            maximum_timeout_seconds=120,
            default_parallel_jobs=1,
            maximum_parallel_jobs=2,
        ),
    )


def test_in_process_client_lists_tools_and_parses_successful_result(tmp_path: Path) -> None:
    result = _result("00000000-0000-0000-0000-000000000201")
    client = InProcessMcpToolClient(create_mcp_server(_dependencies(result=result)))

    tools = client.list_tools()
    record = client.call_tool(
        AgentToolName.SIMULATE_BUILDING,
        {
            "spec": {
                "idf_path": str(tmp_path / "building.idf"),
                "epw_path": str(tmp_path / "weather.epw"),
                "timeout_seconds": 60,
                "parallel_jobs": 1,
            }
        },
    )
    parsed = parse_tool_output(record)

    assert {tool.name for tool in tools} >= {
        "simulate_building",
        "compare_simulations",
        "get_energy_metrics",
        "get_zone_metrics",
        "validate_simulation",
    }
    assert record.success is True
    assert isinstance(parsed, SimulationResult)
    assert parsed.metrics.energy is not None
    assert parsed.metrics.energy.total_site_energy_kwh == 850.0


def test_in_process_client_normalizes_structured_tool_error(tmp_path: Path) -> None:
    client = InProcessMcpToolClient(
        create_mcp_server(
            _dependencies(error=SimulationError(message="Simulation execution failed."))
        )
    )

    record = client.call_tool(
        AgentToolName.SIMULATE_BUILDING,
        {
            "spec": {
                "idf_path": str(tmp_path / "building.idf"),
                "epw_path": str(tmp_path / "weather.epw"),
                "timeout_seconds": 60,
                "parallel_jobs": 1,
            }
        },
    )

    assert isinstance(record, ToolExecutionRecord)
    assert record.success is False
    assert record.error is not None
    assert record.error.error_code == "energyplus.simulation_error"


def test_in_process_client_parses_validation_result_and_unknown_output() -> None:
    warning = ValidationIssue(
        code="simulation.warning",
        message="Validation warning.",
        severity=ValidationSeverity.WARNING,
        target="simulation_spec.idf_path",
        recommendation="Review the IDF file.",
    )
    client = InProcessMcpToolClient(
        create_mcp_server(
            _dependencies(
                result=_result("00000000-0000-0000-0000-000000000202"),
                validation_result=ValidationResult.success(warnings=(warning,)),
            )
        )
    )

    validation_record = client.call_tool(
        AgentToolName.VALIDATE_SIMULATION,
        {
            "spec": {
                "idf_path": "C:/building.idf",
                "epw_path": "C:/weather.epw",
                "timeout_seconds": 60,
                "parallel_jobs": 1,
            }
        },
    )
    unknown_record = ToolExecutionRecord(
        tool_name="unknown_tool",
        arguments={},
        success=True,
        structured_output={"ok": True},
    )

    parsed_validation = parse_tool_output(validation_record)

    assert isinstance(parsed_validation, ValidationResult)
    assert parsed_validation.valid is True
    assert parse_tool_output(unknown_record) is None
