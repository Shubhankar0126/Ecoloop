from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import pytest

from ecoloop_energyplus.application import SimulationService
from ecoloop_energyplus.config.models import (
    EnergyPlusPlatformConfig,
    EnergyPlusSettings,
    OutputSettings,
    SimulationSettings,
)
from ecoloop_energyplus.domain.enums import SimulationStatus
from ecoloop_energyplus.domain.exceptions import (
    EnergyPlusConfigurationError,
    EnergyPlusNotInstalled,
    InvalidIDF,
    InvalidSimulationInput,
    InvalidWeatherFile,
    OutputParseError,
)
from ecoloop_energyplus.domain.models import SimulationResult, SimulationSpec
from ecoloop_energyplus.infrastructure.execution import EnergyPlusRunner, ExecutionResult
from ecoloop_energyplus.infrastructure.locator import (
    CompositeEnergyPlusLocator,
    EnergyPlusLocatorResult,
)
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
)
from ecoloop_energyplus.infrastructure.validation import (
    StartupValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from ecoloop_energyplus.parser.csv import CsvParser, CsvParseResult


def _candidate() -> EnergyPlusInstallationCandidate:
    return EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
        root_path=Path("C:/EnergyPlusV25-1-0"),
        executable_path=Path("C:/EnergyPlusV25-1-0/energyplus.exe"),
        platform=EnergyPlusPlatform.WINDOWS,
        version="25.1.0",
        supported=True,
    )


def _config(output_root: Path, *, validate_on_startup: bool = True) -> EnergyPlusPlatformConfig:
    return EnergyPlusPlatformConfig(
        energyplus=EnergyPlusSettings(validate_on_startup=validate_on_startup),
        simulation=SimulationSettings(
            default_timeout_seconds=60,
            maximum_timeout_seconds=120,
        ),
        output=OutputSettings(root_directory=output_root),
    )


def _write_sql_output(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE TabularDataWithStrings (
                ReportName TEXT,
                TableName TEXT,
                RowName TEXT,
                ColumnName TEXT,
                Units TEXT,
                Value TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO TabularDataWithStrings VALUES (?, ?, ?, ?, ?, ?)",
            (
                (
                    "Annual Report",
                    "Annual Building Utility Performance Summary",
                    "Total Site Energy",
                    "Annual Value",
                    "kWh",
                    "1000",
                ),
                (
                    "Annual Report",
                    "End Uses",
                    "Electricity Consumption",
                    "Annual Value",
                    "kWh",
                    "600",
                ),
            ),
        )
        connection.commit()


def _write_outputs(output_directory: Path) -> None:
    (output_directory / "eplusout.err").write_text(
        "** Warning ** example warning\n",
        encoding="utf-8",
    )
    _write_sql_output(output_directory / "eplusout.sql")
    (output_directory / "eplusout.csv").write_text(
        "\n".join(
            (
                "Date/Time,ZONE ONE:Zone Mean Air Temperature [C](Hourly),"
                "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)",
                "01/01  01:00:00,22,30",
                "01/01  02:00:00,24,32",
            )
        ),
        encoding="utf-8",
    )
    (output_directory / "eplusout.eso").write_text(
        "\n".join(
            (
                "1,2,ZONE ONE,Zone Mean Air Temperature [C] !Hourly",
                "End of Data Dictionary",
                "1,22",
                "1,24",
                "End of Data",
            )
        ),
        encoding="utf-8",
    )
    (output_directory / "eplustbl.htm").write_text(
        """
        <html><body>
          <h2>Monthly Summary</h2>
          <table>
            <tr><th>Month</th><th>Electricity</th></tr>
            <tr><td>January</td><td>100</td></tr>
          </table>
        </body></html>
        """,
        encoding="utf-8",
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
        duration_ms=100,
    )


class StubLocator(CompositeEnergyPlusLocator):
    def __init__(self, result: EnergyPlusLocatorResult) -> None:
        self._result = result

    def locate(self, settings: EnergyPlusSettings) -> EnergyPlusLocatorResult:
        return self._result


class StubStartupValidator(StartupValidator):
    def __init__(self, result: ValidationResult) -> None:
        self._result = result

    def validate(self, config: EnergyPlusPlatformConfig) -> ValidationResult:
        return self._result


class StubRunner(EnergyPlusRunner):
    def __init__(
        self,
        result: ExecutionResult,
        *,
        output_writer: Callable[[Path], None] | None = None,
    ) -> None:
        self._result = result
        self._output_writer = output_writer

    def run(
        self,
        *,
        candidate: EnergyPlusInstallationCandidate,
        spec: SimulationSpec,
        settings: SimulationSettings,
        output_directory: Path,
        working_directory: Path | None = None,
        cancellation_event: Event | None = None,
        environment_overrides: dict[str, str] | None = None,
    ) -> ExecutionResult:
        if self._output_writer is not None:
            self._output_writer(output_directory)

        return self._result


class FailingCsvParser(CsvParser):
    def parse_file(self, path: Path) -> CsvParseResult:
        raise OutputParseError(message="CSV parser failed.")


def _valid_spec(tmp_path: Path) -> SimulationSpec:
    idf_path = tmp_path / "building.idf"
    epw_path = tmp_path / "weather.epw"
    idf_path.write_text("Version,25.1;\n", encoding="utf-8")
    epw_path.write_text("LOCATION,Test\n", encoding="utf-8")
    return SimulationSpec(idf_path=idf_path, epw_path=epw_path)


def test_simulation_service_runs_full_pipeline_with_injected_dependencies(
    tmp_path: Path,
) -> None:
    locator_result = EnergyPlusLocatorResult(selected_candidate=_candidate())
    startup_warning = ValidationIssue(
        code="startup.warning",
        message="Startup warning",
        severity=ValidationSeverity.WARNING,
        target="energyplus",
        recommendation="Proceed.",
    )
    service = SimulationService(
        _config(tmp_path / "runs"),
        locator=StubLocator(locator_result),
        startup_validator=StubStartupValidator(
            ValidationResult.success(warnings=(startup_warning,))
        ),
        runner=StubRunner(_execution_result(), output_writer=_write_outputs),
    )

    result = service.run(_valid_spec(tmp_path))

    assert result.final_status is SimulationStatus.SUCCEEDED
    assert result.metrics.energy is not None
    assert result.metrics.energy.total_site_energy_kwh == pytest.approx(1000.0)
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(23.0)
    assert result.metrics.monthly_summary[0].name == "Monthly Summary"
    assert "Startup warning" in result.diagnostics
    assert "WARNING line 1: example warning" in result.diagnostics
    assert result.metadata.command_line == ("energyplus", "-w", "weather.epw", "building.idf")


def test_simulation_service_reports_missing_outputs_after_successful_execution(
    tmp_path: Path,
) -> None:
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result()),
    )

    result = service.run(_valid_spec(tmp_path))

    assert result.final_status is SimulationStatus.SUCCEEDED
    assert any("eplusout.sql" in diagnostic for diagnostic in result.diagnostics)
    assert any("eplustbl.htm" in diagnostic for diagnostic in result.diagnostics)


def test_simulation_service_returns_parse_failed_result_when_parser_raises(
    tmp_path: Path,
) -> None:
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result(), output_writer=_write_outputs),
        csv_parser=FailingCsvParser(),
    )

    result = service.run(_valid_spec(tmp_path))

    assert isinstance(result, SimulationResult)
    assert result.final_status is SimulationStatus.PARSE_FAILED
    assert "CSV parser failed." in result.diagnostics


def test_simulation_service_raises_input_specific_exception_for_invalid_idf(
    tmp_path: Path,
) -> None:
    invalid_idf_path = tmp_path / "invalid.idf"
    invalid_idf_path.write_text("Building,\n", encoding="utf-8")
    epw_path = tmp_path / "weather.epw"
    epw_path.write_text("LOCATION,Test\n", encoding="utf-8")
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(InvalidIDF, match="Version object"):
        service.run(SimulationSpec(idf_path=invalid_idf_path, epw_path=epw_path))


def test_simulation_service_raises_not_installed_when_startup_validation_fails(
    tmp_path: Path,
) -> None:
    startup_failure = ValidationResult.failure(
        issues=(
            ValidationIssue(
                code="startup.energyplus.installation_unavailable",
                message="No installation.",
                severity=ValidationSeverity.ERROR,
                target="energyplus.installation",
                recommendation="Install EnergyPlus.",
            ),
        )
    )
    service = SimulationService(
        _config(tmp_path / "runs"),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=None)),
        startup_validator=StubStartupValidator(startup_failure),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(EnergyPlusNotInstalled, match="No installation"):
        service.run(_valid_spec(tmp_path))


def test_simulation_service_rejects_disabled_execution(tmp_path: Path) -> None:
    config = EnergyPlusPlatformConfig(
        energyplus=EnergyPlusSettings(enabled=False),
        simulation=SimulationSettings(),
        output=OutputSettings(root_directory=tmp_path / "runs"),
    )
    service = SimulationService(
        config,
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(EnergyPlusConfigurationError, match="disabled"):
        service.run(_valid_spec(tmp_path))


def test_simulation_service_raises_when_locator_has_no_candidate(
    tmp_path: Path,
) -> None:
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(
            EnergyPlusLocatorResult(
                selected_candidate=None,
                selection_diagnostics=("Nothing found.",),
            )
        ),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(EnergyPlusNotInstalled, match="No supported EnergyPlus installation"):
        service.run(_valid_spec(tmp_path))


def test_simulation_service_raises_configuration_error_for_startup_configuration_failure(
    tmp_path: Path,
) -> None:
    startup_failure = ValidationResult.failure(
        issues=(
            ValidationIssue(
                code="startup.configuration.invalid_preferred_version",
                message="Preferred version is invalid.",
                severity=ValidationSeverity.ERROR,
                target="config.energyplus.preferred_version",
                recommendation="Use a valid version.",
            ),
        )
    )
    service = SimulationService(
        _config(tmp_path / "runs"),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        startup_validator=StubStartupValidator(startup_failure),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(EnergyPlusConfigurationError, match="Preferred version is invalid"):
        service.run(_valid_spec(tmp_path))


def test_simulation_service_raises_weather_exception_for_invalid_epw(
    tmp_path: Path,
) -> None:
    idf_path = tmp_path / "building.idf"
    idf_path.write_text("Version,25.1;\n", encoding="utf-8")
    epw_path = tmp_path / "weather.epw"
    epw_path.write_text("INVALID HEADER\n", encoding="utf-8")
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(InvalidWeatherFile, match="LOCATION header"):
        service.run(SimulationSpec(idf_path=idf_path, epw_path=epw_path))


def test_simulation_service_raises_generic_input_exception_for_parallel_job_policy(
    tmp_path: Path,
) -> None:
    service = SimulationService(
        _config(tmp_path / "runs", validate_on_startup=False),
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result()),
    )

    with pytest.raises(InvalidSimulationInput, match="parallel jobs"):
        service.run(
            SimulationSpec(
                idf_path=_valid_spec(tmp_path).idf_path,
                epw_path=_valid_spec(tmp_path).epw_path,
                parallel_jobs=0,
            )
        )


def test_simulation_service_preserves_failed_status_and_skips_stdout_stderr_persistence(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs"
    config = EnergyPlusPlatformConfig(
        energyplus=EnergyPlusSettings(validate_on_startup=False),
        simulation=SimulationSettings(default_timeout_seconds=60, maximum_timeout_seconds=120),
        output=OutputSettings(root_directory=output_root, keep_stdout_stderr=False),
    )
    service = SimulationService(
        config,
        locator=StubLocator(EnergyPlusLocatorResult(selected_candidate=_candidate())),
        runner=StubRunner(_execution_result(SimulationStatus.FAILED)),
    )

    result = service.run(_valid_spec(tmp_path))
    run_directories = tuple(output_root.iterdir())

    assert result.final_status is SimulationStatus.FAILED
    assert len(run_directories) == 1
    assert (run_directories[0] / "logs" / "stdout.log").exists() is False


def test_simulation_service_end_to_end_if_energyplus_and_sample_inputs_are_available(
    tmp_path: Path,
) -> None:
    locator_result = CompositeEnergyPlusLocator().locate(EnergyPlusSettings())
    idf_path_value = os.getenv("ECOLOOP_ENERGYPLUS_E2E_IDF")
    epw_path_value = os.getenv("ECOLOOP_ENERGYPLUS_E2E_EPW")
    if locator_result.selected_candidate is None:
        pytest.skip("EnergyPlus is not installed locally.")

    if not idf_path_value or not epw_path_value:
        pytest.skip("E2E input paths were not provided in environment variables.")

    idf_path = Path(idf_path_value)
    epw_path = Path(epw_path_value)
    if not idf_path.exists() or not epw_path.exists():
        pytest.skip("Configured E2E input paths do not exist.")

    service = SimulationService(
        EnergyPlusPlatformConfig(
            energyplus=EnergyPlusSettings(validate_on_startup=True),
            simulation=SimulationSettings(default_timeout_seconds=600, maximum_timeout_seconds=600),
            output=OutputSettings(root_directory=tmp_path / "runs"),
        )
    )

    result = service.run(
        SimulationSpec(
            idf_path=idf_path,
            epw_path=epw_path,
            timeout_seconds=600,
        )
    )

    assert result.metadata.command_line
    assert result.final_status in {
        SimulationStatus.SUCCEEDED,
        SimulationStatus.FAILED,
        SimulationStatus.PARSE_FAILED,
        SimulationStatus.TIMED_OUT,
    }
