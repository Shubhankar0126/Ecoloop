"""Framework-independent EnergyPlus simulation orchestration service."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Never
from uuid import UUID, uuid4

from ecoloop_energyplus.application.result_assembler import SimulationResultAssembler
from ecoloop_energyplus.config.models import EnergyPlusPlatformConfig
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
from ecoloop_energyplus.infrastructure.locator import CompositeEnergyPlusLocator
from ecoloop_energyplus.infrastructure.output import OutputManager, RunDirectory
from ecoloop_energyplus.infrastructure.validation import (
    InputValidator,
    StartupValidator,
    ValidationIssue,
    ValidationResult,
)
from ecoloop_energyplus.parser.csv import CsvParser, CsvParseResult
from ecoloop_energyplus.parser.err import ErrDiagnosticsReport, ErrParser
from ecoloop_energyplus.parser.eso import EsoParser, EsoParseResult
from ecoloop_energyplus.parser.sql import SqlParser, SqlParseResult
from ecoloop_energyplus.parser.summary import SummaryParser, SummaryParseResult


class SimulationService:
    """The single public entry point for running EnergyPlus simulations."""

    def __init__(
        self,
        config: EnergyPlusPlatformConfig,
        *,
        locator: CompositeEnergyPlusLocator | None = None,
        startup_validator: StartupValidator | None = None,
        input_validator: InputValidator | None = None,
        runner: EnergyPlusRunner | None = None,
        output_manager: OutputManager | None = None,
        err_parser: ErrParser | None = None,
        sql_parser: SqlParser | None = None,
        csv_parser: CsvParser | None = None,
        eso_parser: EsoParser | None = None,
        summary_parser: SummaryParser | None = None,
        result_assembler: SimulationResultAssembler | None = None,
        simulation_id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        """Initialize the service with injectable infrastructure dependencies."""
        self._config = config
        self._locator = locator or CompositeEnergyPlusLocator()
        self._startup_validator = startup_validator or StartupValidator(locator=self._locator)
        self._input_validator = input_validator or InputValidator()
        self._runner = runner or EnergyPlusRunner()
        self._output_manager = output_manager or OutputManager(config.output)
        self._err_parser = err_parser or ErrParser()
        self._sql_parser = sql_parser or SqlParser()
        self._csv_parser = csv_parser or CsvParser()
        self._eso_parser = eso_parser or EsoParser()
        self._summary_parser = summary_parser or SummaryParser()
        self._result_assembler = result_assembler or SimulationResultAssembler()
        self._simulation_id_factory = simulation_id_factory or uuid4

    def run(
        self,
        spec: SimulationSpec,
        *,
        cancellation_event: Event | None = None,
    ) -> SimulationResult:
        """Validate, execute, parse, and assemble one EnergyPlus simulation result."""
        if not self._config.energyplus.enabled:
            raise EnergyPlusConfigurationError(
                message="EnergyPlus simulation execution is disabled in the current configuration.",
                context={"enabled": self._config.energyplus.enabled},
            )

        startup_diagnostics = self._validate_startup()
        self._validate_inputs(spec)

        locator_result = self._locator.locate(self._config.energyplus)
        candidate = locator_result.selected_candidate
        if candidate is None:
            raise EnergyPlusNotInstalled(
                message="No supported EnergyPlus installation is available for execution.",
                context={"diagnostics": list(locator_result.selection_diagnostics)},
            )

        run_directory = self._output_manager.create_run_directory(prefix="simulation")
        self._output_manager.stage_input_artifacts(run_directory, spec)
        execution_result = self._runner.run(
            candidate=candidate,
            spec=spec,
            settings=self._config.simulation,
            output_directory=run_directory.output_path,
            working_directory=run_directory.root_path,
            cancellation_event=cancellation_event,
        )
        self._persist_execution_logs(run_directory, execution_result)
        manifest = self._output_manager.write_artifact_manifest(run_directory)

        err_report: ErrDiagnosticsReport | None = None
        sql_result = SqlParseResult.empty(source=run_directory.output_path / "eplusout.sql")
        csv_result = CsvParseResult.empty(source=run_directory.output_path / "eplusout.csv")
        eso_result = EsoParseResult.empty(source=run_directory.output_path / "eplusout.eso")
        summary_result = SummaryParseResult.empty(
            source=run_directory.output_path / "eplustbl.htm"
        )
        parse_error: OutputParseError | None = None

        try:
            err_report = self._parse_optional_err(run_directory)
            sql_result = self._parse_optional_sql(run_directory)
            csv_result = self._parse_optional_csv(run_directory)
            eso_result = self._parse_optional_eso(run_directory)
            summary_result = self._parse_optional_summary(run_directory)
            result = self._result_assembler.assemble(
                simulation_id=self._simulation_id_factory(),
                spec=spec,
                candidate=candidate,
                execution_result=execution_result,
                artifacts=manifest.artifacts,
                err_report=err_report,
                sql_result=sql_result,
                csv_result=csv_result,
                eso_result=eso_result,
                summary_result=summary_result,
                additional_diagnostics=(
                    startup_diagnostics
                    + self._missing_artifact_diagnostics(
                        run_directory,
                        execution_result.status,
                    )
                ),
            )
        except OutputParseError as error:
            parse_error = error
            result = self._result_assembler.assemble(
                simulation_id=self._simulation_id_factory(),
                spec=spec,
                candidate=candidate,
                execution_result=execution_result,
                artifacts=manifest.artifacts,
                err_report=err_report,
                sql_result=sql_result,
                csv_result=csv_result,
                eso_result=eso_result,
                summary_result=summary_result,
                additional_diagnostics=startup_diagnostics,
                parse_error=parse_error,
            )

        self._output_manager.cleanup_run_directory(
            run_directory,
            status=result.final_status,
            completed_at=result.metadata.completed_at,
        )
        return result

    def _validate_startup(self) -> tuple[str, ...]:
        """Run startup validation when configured and return warning diagnostics."""
        if not self._config.energyplus.validate_on_startup:
            return ()

        startup_result = self._startup_validator.validate(self._config)
        if startup_result.valid:
            return tuple(warning.message for warning in startup_result.warnings)

        self._raise_startup_validation_error(startup_result)

    def _validate_inputs(self, spec: SimulationSpec) -> None:
        """Validate one simulation specification and raise the appropriate package error."""
        validation_result = self._input_validator.validate(spec, self._config.simulation)
        if validation_result.valid:
            return

        self._raise_input_validation_error(validation_result)

    def _persist_execution_logs(
        self,
        run_directory: RunDirectory,
        execution_result: ExecutionResult,
    ) -> None:
        """Persist captured stdout and stderr when configured to retain them."""
        if not self._config.output.keep_stdout_stderr:
            return

        run_directory.stdout_path.write_text(execution_result.stdout, encoding="utf-8")
        run_directory.stderr_path.write_text(execution_result.stderr, encoding="utf-8")

    def _parse_optional_err(self, run_directory: RunDirectory) -> ErrDiagnosticsReport | None:
        """Parse an ERR artifact when one exists in the run directory."""
        err_path = run_directory.output_path / "eplusout.err"
        if not err_path.exists():
            return None

        return self._err_parser.parse_file(err_path)

    def _parse_optional_sql(self, run_directory: RunDirectory) -> SqlParseResult:
        """Parse a SQLite artifact when it exists, otherwise return an empty result."""
        sql_path = run_directory.output_path / "eplusout.sql"
        if not sql_path.exists():
            return SqlParseResult.empty(source=sql_path)

        return self._sql_parser.parse_file(sql_path)

    def _parse_optional_csv(self, run_directory: RunDirectory) -> CsvParseResult:
        """Parse a CSV artifact when it exists, otherwise return an empty result."""
        csv_path = run_directory.output_path / "eplusout.csv"
        if not csv_path.exists():
            return CsvParseResult.empty(source=csv_path)

        return self._csv_parser.parse_file(csv_path)

    def _parse_optional_eso(self, run_directory: RunDirectory) -> EsoParseResult:
        """Parse an ESO artifact when it exists, otherwise return an empty result."""
        eso_path = run_directory.output_path / "eplusout.eso"
        if not eso_path.exists():
            return EsoParseResult.empty(source=eso_path)

        return self._eso_parser.parse_file(eso_path)

    def _parse_optional_summary(self, run_directory: RunDirectory) -> SummaryParseResult:
        """Parse a summary artifact when one of the supported filenames exists."""
        for candidate_path in (
            run_directory.output_path / "eplustbl.htm",
            run_directory.output_path / "eplustbl.html",
        ):
            if candidate_path.exists():
                return self._summary_parser.parse_file(candidate_path)

        return SummaryParseResult.empty(source=run_directory.output_path / "eplustbl.htm")

    def _missing_artifact_diagnostics(
        self,
        run_directory: RunDirectory,
        status: SimulationStatus,
    ) -> tuple[str, ...]:
        """Report missing commonly expected output artifacts after a successful run."""
        if status is not SimulationStatus.SUCCEEDED:
            return ()

        expected_paths = (
            run_directory.output_path / "eplusout.err",
            run_directory.output_path / "eplusout.sql",
            run_directory.output_path / "eplusout.csv",
            run_directory.output_path / "eplusout.eso",
        )
        diagnostics = [
            f"Expected EnergyPlus output artifact was not produced: {path.name}."
            for path in expected_paths
            if not path.exists()
        ]
        if not any(
            path.exists()
            for path in (
                run_directory.output_path / "eplustbl.htm",
                run_directory.output_path / "eplustbl.html",
            )
        ):
            diagnostics.append(
                "Expected EnergyPlus summary artifact was not produced: "
                "eplustbl.htm."
            )

        return tuple(diagnostics)

    def _raise_startup_validation_error(self, result: ValidationResult) -> Never:
        """Raise the correct package exception for a startup validation failure."""
        primary_issue = result.issues[0]
        if primary_issue.code == "startup.energyplus.installation_unavailable":
            raise EnergyPlusNotInstalled(
                message=primary_issue.message,
                context=self._validation_context(result),
            )

        raise EnergyPlusConfigurationError(
            message=primary_issue.message,
            context=self._validation_context(result),
        )

    def _raise_input_validation_error(self, result: ValidationResult) -> Never:
        """Raise the correct package exception for an input validation failure."""
        primary_issue = result.issues[0]
        if "idf" in primary_issue.target:
            raise InvalidIDF(
                message=primary_issue.message,
                context=self._validation_context(result),
            )

        if "epw" in primary_issue.target:
            raise InvalidWeatherFile(
                message=primary_issue.message,
                context=self._validation_context(result),
            )

        raise InvalidSimulationInput(
            message=primary_issue.message,
            context=self._validation_context(result),
        )

    def _validation_context(self, result: ValidationResult) -> dict[str, object]:
        """Serialize structured validation issues and warnings into exception context."""
        return {
            "issues": [self._issue_as_dict(issue) for issue in result.issues],
            "warnings": [self._issue_as_dict(issue) for issue in result.warnings],
        }

    @staticmethod
    def _issue_as_dict(issue: ValidationIssue) -> dict[str, object]:
        """Serialize one validation issue for exception context payloads."""
        return {
            "code": issue.code,
            "message": issue.message,
            "target": issue.target,
            "recommendation": issue.recommendation,
            "severity": issue.severity.value,
        }


__all__ = ["SimulationService"]
