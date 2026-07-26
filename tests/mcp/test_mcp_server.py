from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import anyio
import pytest
from pydantic import BaseModel, ConfigDict

from ecoloop_common.exceptions import (
    ApplicationError,
    DomainError,
    InfrastructureError,
    UnexpectedError,
)
from ecoloop_energyplus import (
    ComfortMetrics,
    EnergyMetrics,
    EnergyPlusConfigurationError,
    HVACMetrics,
    InputValidator,
    InvalidSimulationInput,
    OutputParseError,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationService,
    SimulationSettings,
    SimulationSpec,
    SimulationStatus,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    WeatherMetrics,
    ZoneMetrics,
)
from ecoloop_energyplus.domain.exceptions import SimulationError
from ecoloop_mcp import (
    McpServerDependencies,
    ToolRegistration,
    ToolRegistry,
    build_tool_registrations,
    create_mcp_server,
)
from ecoloop_mcp.tools.compare_simulations import ComparisonResult
from ecoloop_mcp.tools.get_zone_metrics import ZoneMetricsCollection
from mcp import types


class StubSimulationService:
    """Minimal simulation service stub for MCP tool testing."""

    def __init__(
        self,
        *,
        result: SimulationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[SimulationSpec] = []

    def run(self, spec: SimulationSpec) -> SimulationResult:
        self.calls.append(spec)
        if self._error is not None:
            raise self._error

        assert self._result is not None
        return self._result


class StubInputValidator:
    """Minimal validation stub for the MCP validation-only tool."""

    def __init__(self, result: ValidationResult) -> None:
        self._result = result
        self.calls: list[tuple[SimulationSpec, SimulationSettings]] = []

    def validate(self, spec: SimulationSpec, settings: SimulationSettings) -> ValidationResult:
        self.calls.append((spec, settings))
        return self._result


def _simulation_settings() -> SimulationSettings:
    return SimulationSettings(
        default_timeout_seconds=60,
        maximum_timeout_seconds=120,
        default_parallel_jobs=1,
        maximum_parallel_jobs=4,
    )


def _spec(tmp_path: Path) -> SimulationSpec:
    return SimulationSpec(
        idf_path=tmp_path / "building.idf",
        epw_path=tmp_path / "weather.epw",
        timeout_seconds=90,
        parallel_jobs=2,
    )


def _result(
    simulation_id: str,
    *,
    energy_total: float | None = 1000.0,
    electricity: float | None = 600.0,
    heating: float | None = 150.0,
    cooling: float | None = 200.0,
    hvac_total: float | None = 350.0,
    equipment: float | None = 90.0,
    temperature: float | None = 23.0,
    humidity: float | None = 45.0,
    pmv: float | None = 0.2,
    ppd: float | None = 8.0,
    dry_bulb: float | None = 31.0,
    outdoor_humidity: float | None = 55.0,
    zones: tuple[ZoneMetrics, ...] | None = None,
) -> SimulationResult:
    return SimulationResult(
        simulation_id=UUID(simulation_id),
        final_status=SimulationStatus.SUCCEEDED,
        metrics=SimulationMetrics(
            energy=EnergyMetrics(
                total_site_energy_kwh=energy_total,
                electricity_consumption_kwh=electricity,
            )
            if energy_total is not None or electricity is not None
            else None,
            hvac=HVACMetrics(
                heating_energy_kwh=heating,
                cooling_energy_kwh=cooling,
                hvac_energy_kwh=hvac_total,
                equipment_loads_kwh=equipment,
            )
            if any(value is not None for value in (heating, cooling, hvac_total, equipment))
            else None,
            comfort=ComfortMetrics(
                average_zone_temperature_celsius=temperature,
                average_zone_humidity_percent=humidity,
                average_pmv=pmv,
                average_ppd_percent=ppd,
            )
            if any(value is not None for value in (temperature, humidity, pmv, ppd))
            else None,
            weather=WeatherMetrics(
                average_outdoor_dry_bulb_celsius=dry_bulb,
                average_outdoor_relative_humidity_percent=outdoor_humidity,
            )
            if dry_bulb is not None or outdoor_humidity is not None
            else None,
            zones=zones
            or (
                ZoneMetrics(
                    zone_name="ZONE ONE",
                    mean_air_temperature_celsius=22.5,
                    mean_relative_humidity_percent=40.0,
                    thermal_comfort_pmv=0.1,
                    thermal_comfort_ppd_percent=6.0,
                ),
            ),
        ),
        artifacts=(),
        diagnostics=("Simulation completed.",),
        metadata=SimulationMetadata(
            energyplus_version="25.1.0",
            command_line=("energyplus", "-w", "weather.epw", "building.idf"),
            exit_code=0,
            duration_ms=500,
            started_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 26, 9, 1, tzinfo=UTC),
        ),
    )


def _dependencies(
    tmp_path: Path,
    *,
    result: SimulationResult | None = None,
    service_error: Exception | None = None,
    validation_result: ValidationResult | None = None,
) -> tuple[McpServerDependencies, StubSimulationService, StubInputValidator]:
    service = StubSimulationService(
        result=result or _result("00000000-0000-0000-0000-000000000001"),
        error=service_error,
    )
    validator = StubInputValidator(validation_result or ValidationResult.success())
    dependencies = McpServerDependencies(
        simulation_service=cast(SimulationService, service),
        input_validator=cast(InputValidator, validator),
        simulation_settings=_simulation_settings(),
    )
    return dependencies, service, validator


def _structured_content(result: types.CallToolResult) -> dict[str, object]:
    structured = result.structuredContent
    assert structured is not None
    return cast(dict[str, object], structured)


def _list_server_tools(server: Any) -> list[types.Tool]:
    async def list_tools() -> list[types.Tool]:
        response = await server.request_handlers[types.ListToolsRequest](types.ListToolsRequest())
        return cast(list[types.Tool], response.root.tools)

    return anyio.run(list_tools)


def _call_server_tool(server: Any, name: str, arguments: dict[str, object]) -> types.CallToolResult:
    async def call_tool() -> types.CallToolResult:
        response = await server.request_handlers[types.CallToolRequest](
            types.CallToolRequest(
                params=types.CallToolRequestParams(name=name, arguments=arguments)
            )
        )
        return cast(types.CallToolResult, response.root)

    return anyio.run(call_tool)


def test_build_tool_registrations_exposes_expected_tool_names(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)

    registrations = build_tool_registrations(dependencies)

    assert [registration.name for registration in registrations] == [
        "simulate_building",
        "compare_simulations",
        "get_energy_metrics",
        "get_zone_metrics",
        "validate_simulation",
    ]


def test_tool_registry_rejects_duplicate_names() -> None:
    class EmptyInput(BaseModel):
        model_config = ConfigDict(frozen=True)
        request_id: str

    class OutputModel(BaseModel):
        model_config = ConfigDict(frozen=True)
        ok: bool

    registration = ToolRegistration(
        name="duplicate",
        title="Duplicate",
        description="Duplicate tool.",
        input_model=EmptyInput,
        output_model=OutputModel,
        handler=lambda payload: OutputModel(ok=True),
    )

    with pytest.raises(ValueError, match="Duplicate MCP tool registration"):
        ToolRegistry((registration, registration))


def test_simulate_building_tool_executes_injected_service(tmp_path: Path) -> None:
    expected_result = _result("00000000-0000-0000-0000-000000000010")
    dependencies, service, _ = _dependencies(tmp_path, result=expected_result)
    registry = ToolRegistry(build_tool_registrations(dependencies))
    spec = _spec(tmp_path)

    result = registry.call_tool(
        "simulate_building",
        {"spec": spec.model_dump(mode="json")},
    )

    payload = _structured_content(result)
    assert result.isError is False
    assert payload["simulation_id"] == "00000000-0000-0000-0000-000000000010"
    assert service.calls == [spec]


def test_validate_simulation_tool_uses_injected_validator_only(tmp_path: Path) -> None:
    warning = ValidationIssue(
        code="simulation.input.warning",
        message="Validation warning.",
        severity=ValidationSeverity.WARNING,
        target="simulation_spec.idf_path",
        recommendation="Review the IDF contents.",
    )
    dependencies, service, validator = _dependencies(
        tmp_path,
        validation_result=ValidationResult.success(warnings=(warning,)),
    )
    registry = ToolRegistry(build_tool_registrations(dependencies))
    spec = _spec(tmp_path)

    result = registry.call_tool(
        "validate_simulation",
        {"spec": spec.model_dump(mode="json")},
    )

    payload = _structured_content(result)
    assert result.isError is False
    assert payload["valid"] is True
    assert service.calls == []
    assert validator.calls == [(spec, dependencies.simulation_settings)]


def test_tool_registry_returns_typed_protocol_error_for_invalid_arguments(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)
    registry = ToolRegistry(build_tool_registrations(dependencies))

    result = registry.call_tool("simulate_building", {})

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["error_code"] == "mcp.invalid_arguments"
    assert payload["category"] == "protocol"
    errors = cast(list[dict[str, object]], payload["details"]["errors"])  # type: ignore[index]
    assert errors[0]["location"] == "spec"


def test_tool_registry_returns_typed_protocol_error_for_unknown_tool(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)
    registry = ToolRegistry(build_tool_registrations(dependencies))

    result = registry.call_tool("does_not_exist", {})

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["error_code"] == "mcp.tool_not_found"
    assert payload["category"] == "protocol"


@pytest.mark.parametrize(
    ("error", "expected_category"),
    [
        (InvalidSimulationInput(message="Invalid input."), "validation"),
        (EnergyPlusConfigurationError(message="Invalid configuration."), "configuration"),
        (SimulationError(message="Simulation failed."), "simulation"),
        (OutputParseError(message="Output parsing failed."), "simulation"),
        (InfrastructureError("Filesystem unavailable."), "infrastructure"),
        (ApplicationError("Orchestration failed."), "application"),
        (DomainError("Domain rule broken."), "domain"),
        (UnexpectedError(), "unexpected"),
    ],
)
def test_tool_registry_maps_ecoloop_errors_to_typed_results(
    error: Exception,
    expected_category: str,
) -> None:
    class EmptyInput(BaseModel):
        model_config = ConfigDict(frozen=True)
        request_id: str

    class OutputModel(BaseModel):
        model_config = ConfigDict(frozen=True)
        ok: bool

    def handler(payload: EmptyInput) -> OutputModel:
        raise error

    registry = ToolRegistry(
        (
            ToolRegistration(
                name="failing_tool",
                title="Failing Tool",
                description="Raises a shared exception.",
                input_model=EmptyInput,
                output_model=OutputModel,
                handler=handler,
            ),
        )
    )

    result = registry.call_tool("failing_tool", {"request_id": "req-1"})

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["category"] == expected_category


def test_tool_registry_maps_unexpected_errors_to_typed_results() -> None:
    class EmptyInput(BaseModel):
        model_config = ConfigDict(frozen=True)
        request_id: str

    class OutputModel(BaseModel):
        model_config = ConfigDict(frozen=True)
        ok: bool

    def handler(payload: EmptyInput) -> OutputModel:
        raise RuntimeError("boom")

    registry = ToolRegistry(
        (
            ToolRegistration(
                name="runtime_failure",
                title="Runtime Failure",
                description="Raises a runtime error.",
                input_model=EmptyInput,
                output_model=OutputModel,
                handler=handler,
            ),
        )
    )

    result = registry.call_tool("runtime_failure", {"request_id": "req-2"})

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["error_code"] == "ecoloop.unexpected_error"
    assert payload["category"] == "unexpected"


def test_tool_registry_maps_invalid_output_to_typed_results() -> None:
    class EmptyInput(BaseModel):
        model_config = ConfigDict(frozen=True)
        request_id: str

    class OutputModel(BaseModel):
        model_config = ConfigDict(frozen=True)
        value: int

    def handler(payload: EmptyInput) -> dict[str, object]:
        return {"value": "invalid"}

    registry = ToolRegistry(
        (
            ToolRegistration(
                name="bad_output",
                title="Bad Output",
                description="Returns an invalid payload.",
                input_model=EmptyInput,
                output_model=OutputModel,
                handler=handler,
            ),
        )
    )

    result = registry.call_tool("bad_output", {"request_id": "req-3"})

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["error_code"] == "mcp.invalid_tool_output"


def test_compare_simulations_returns_normalized_metric_deltas(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)
    registry = ToolRegistry(build_tool_registrations(dependencies))
    baseline = _result("00000000-0000-0000-0000-000000000011")
    candidate = _result(
        "00000000-0000-0000-0000-000000000012",
        energy_total=900.0,
        electricity=500.0,
        heating=120.0,
        cooling=180.0,
        hvac_total=300.0,
        equipment=80.0,
        temperature=22.0,
        humidity=42.0,
        pmv=0.1,
        ppd=7.0,
        dry_bulb=29.0,
        outdoor_humidity=50.0,
    )

    result = registry.call_tool(
        "compare_simulations",
        {
            "baseline": baseline.model_dump(mode="json"),
            "candidate": candidate.model_dump(mode="json"),
        },
    )

    payload = ComparisonResult.model_validate(_structured_content(result))
    assert result.isError is False
    assert payload.energy.total_site_energy_kwh.delta == pytest.approx(-100.0)
    assert payload.hvac.hvac_energy_kwh.delta == pytest.approx(-50.0)
    assert payload.comfort.average_zone_temperature_celsius.delta == pytest.approx(-1.0)
    assert payload.weather.average_outdoor_dry_bulb_celsius.delta == pytest.approx(-2.0)


def test_get_energy_metrics_returns_empty_model_when_energy_is_missing(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)
    registry = ToolRegistry(build_tool_registrations(dependencies))
    result_without_energy = _result(
        "00000000-0000-0000-0000-000000000013",
        energy_total=None,
        electricity=None,
    )

    result = registry.call_tool(
        "get_energy_metrics",
        {"result": result_without_energy.model_dump(mode="json")},
    )

    payload = EnergyMetrics.model_validate(_structured_content(result))
    assert result.isError is False
    assert payload.total_site_energy_kwh is None
    assert payload.electricity_consumption_kwh is None


def test_get_zone_metrics_returns_zone_collection(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(tmp_path)
    registry = ToolRegistry(build_tool_registrations(dependencies))
    simulation_result = _result(
        "00000000-0000-0000-0000-000000000014",
        zones=(
            ZoneMetrics(
                zone_name="ZONE ONE",
                mean_air_temperature_celsius=22.0,
            ),
            ZoneMetrics(
                zone_name="ZONE TWO",
                mean_air_temperature_celsius=24.0,
            ),
        ),
    )

    result = registry.call_tool(
        "get_zone_metrics",
        {"result": simulation_result.model_dump(mode="json")},
    )

    payload = ZoneMetricsCollection.model_validate(_structured_content(result))
    assert result.isError is False
    assert [zone.zone_name for zone in payload.zones] == ["ZONE ONE", "ZONE TWO"]


def test_create_mcp_server_lists_and_executes_registered_tools(tmp_path: Path) -> None:
    expected_result = _result("00000000-0000-0000-0000-000000000015")
    dependencies, service, _ = _dependencies(tmp_path, result=expected_result)
    server = create_mcp_server(dependencies)
    spec = _spec(tmp_path)

    tools = _list_server_tools(server)
    result = _call_server_tool(
        server,
        "simulate_building",
        {"spec": spec.model_dump(mode="json")},
    )

    payload = _structured_content(result)
    assert {tool.name for tool in tools} == {
        "simulate_building",
        "compare_simulations",
        "get_energy_metrics",
        "get_zone_metrics",
        "validate_simulation",
    }
    assert result.isError is False
    assert payload["simulation_id"] == "00000000-0000-0000-0000-000000000015"
    assert service.calls == [spec]


def test_server_returns_structured_error_results_for_failed_execution(tmp_path: Path) -> None:
    dependencies, _, _ = _dependencies(
        tmp_path,
        service_error=SimulationError(message="Simulation failed."),
    )
    server = create_mcp_server(dependencies)

    result = _call_server_tool(
        server,
        "simulate_building",
        {"spec": _spec(tmp_path).model_dump(mode="json")},
    )

    payload = _structured_content(result)
    assert result.isError is True
    assert payload["error_code"] == "energyplus.simulation_error"
    assert payload["category"] == "simulation"
