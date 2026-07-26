from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ecoloop_energyplus.application import SimulationResultAssembler
from ecoloop_energyplus.domain.enums import SimulationArtifactKind, SimulationStatus
from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.domain.models import (
    EnergyMetrics,
    SimulationArtifact,
    SimulationMetrics,
    SimulationMetricValue,
    SimulationSpec,
    WeatherMetrics,
    ZoneMetrics,
)
from ecoloop_energyplus.infrastructure.execution import ExecutionResult
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
)
from ecoloop_energyplus.parser.csv import CsvParseResult
from ecoloop_energyplus.parser.err import ErrDiagnostic, ErrDiagnosticsReport, ErrSeverity
from ecoloop_energyplus.parser.sql import SqlParseResult


def _candidate() -> EnergyPlusInstallationCandidate:
    return EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
        root_path=Path("C:/EnergyPlusV25-1-0"),
        executable_path=Path("C:/EnergyPlusV25-1-0/energyplus.exe"),
        platform=EnergyPlusPlatform.WINDOWS,
        version="25.1.0",
        supported=True,
    )


def _execution_result(status: SimulationStatus = SimulationStatus.SUCCEEDED) -> ExecutionResult:
    return ExecutionResult(
        command_line=("energyplus", "-w", "weather.epw", "building.idf"),
        working_directory=Path("C:/runs/simulation"),
        status=status,
        exit_code=0 if status is SimulationStatus.SUCCEEDED else 1,
        stdout="stdout",
        stderr="stderr",
        diagnostics=("execution diagnostic",),
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
        duration_ms=500,
    )


def _artifacts() -> tuple[SimulationArtifact, ...]:
    return (
        SimulationArtifact(
            artifact_id="idf-copy",
            kind=SimulationArtifactKind.INPUT,
            relative_path=Path("input/building.idf"),
            checksum="idf-checksum",
        ),
        SimulationArtifact(
            artifact_id="epw-copy",
            kind=SimulationArtifactKind.INPUT,
            relative_path=Path("input/weather.epw"),
            checksum="epw-checksum",
        ),
    )


def test_result_assembler_merges_parser_outputs_and_err_diagnostics() -> None:
    assembler = SimulationResultAssembler(hostname_provider=lambda: "test-host")
    simulation_id = uuid4()
    spec = SimulationSpec(idf_path=Path("building.idf"), epw_path=Path("weather.epw"))
    sql_result = SqlParseResult(
        metrics=SimulationMetrics(
            values={
                "energy.total_site_energy_kwh": SimulationMetricValue(value=100.0, unit="kWh")
            },
            energy=EnergyMetrics(total_site_energy_kwh=100.0, electricity_consumption_kwh=60.0),
        ),
        diagnostics=("sql diagnostic",),
    )
    csv_result = CsvParseResult(
        metrics=SimulationMetrics(
            values={
                "weather.average_outdoor_dry_bulb_celsius": SimulationMetricValue(
                    value=31.0,
                    unit="C",
                )
            },
            energy=EnergyMetrics(total_site_energy_kwh=200.0, electricity_consumption_kwh=80.0),
            weather=WeatherMetrics(average_outdoor_dry_bulb_celsius=31.0),
            zones=(
                ZoneMetrics(
                    zone_name="ZONE ONE",
                    mean_air_temperature_celsius=23.0,
                ),
            ),
        ),
        diagnostics=("csv diagnostic",),
    )
    err_report = ErrDiagnosticsReport.from_diagnostics(
        (
            ErrDiagnostic(
                severity=ErrSeverity.FATAL,
                message="Simulation encountered a fatal error.",
                line_number=4,
                raw_line="** Fatal ** Simulation encountered a fatal error.",
            ),
        )
    )

    result = assembler.assemble(
        simulation_id=simulation_id,
        spec=spec,
        candidate=_candidate(),
        execution_result=_execution_result(),
        artifacts=_artifacts(),
        err_report=err_report,
        sql_result=sql_result,
        csv_result=csv_result,
        additional_diagnostics=("startup warning",),
    )

    assert result.simulation_id == simulation_id
    assert result.final_status is SimulationStatus.FAILED
    assert result.metrics.energy is not None
    assert result.metrics.energy.total_site_energy_kwh == pytest.approx(100.0)
    assert result.metrics.weather is not None
    assert result.metrics.weather.average_outdoor_dry_bulb_celsius == pytest.approx(31.0)
    assert result.metrics.zones[0].zone_name == "ZONE ONE"
    assert result.metadata.hostname == "test-host"
    assert result.metadata.idf_checksum == "idf-checksum"
    assert result.metadata.epw_checksum == "epw-checksum"
    assert "startup warning" in result.diagnostics
    assert "sql diagnostic" in result.diagnostics
    assert "csv diagnostic" in result.diagnostics
    assert "FATAL line 4: Simulation encountered a fatal error." in result.diagnostics


def test_result_assembler_marks_parse_failures_explicitly() -> None:
    assembler = SimulationResultAssembler(hostname_provider=lambda: "test-host")
    result = assembler.assemble(
        simulation_id=uuid4(),
        spec=SimulationSpec(idf_path=Path("building.idf"), epw_path=Path("weather.epw")),
        candidate=_candidate(),
        execution_result=_execution_result(),
        artifacts=_artifacts(),
        parse_error=OutputParseError(message="Parser exploded."),
    )

    assert result.final_status is SimulationStatus.PARSE_FAILED
    assert "Parser exploded." in result.diagnostics


def test_result_assembler_preserves_non_success_execution_status_and_missing_checksums() -> None:
    assembler = SimulationResultAssembler(hostname_provider=lambda: "test-host")
    result = assembler.assemble(
        simulation_id=uuid4(),
        spec=SimulationSpec(idf_path=Path("building.idf"), epw_path=Path("weather.epw")),
        candidate=_candidate(),
        execution_result=_execution_result(SimulationStatus.CANCELLED),
        artifacts=(
            SimulationArtifact(
                artifact_id="stdout-log",
                kind=SimulationArtifactKind.LOG,
                relative_path=Path("logs/stdout.log"),
            ),
        ),
    )

    assert result.final_status is SimulationStatus.CANCELLED
    assert result.metadata.idf_checksum is None
    assert result.metadata.epw_checksum is None
