"""Assemble one normalized ``SimulationResult`` from parser and execution outputs."""

from __future__ import annotations

import socket
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from ecoloop_energyplus.domain.enums import SimulationArtifactKind, SimulationStatus
from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.domain.models import (
    SimulationArtifact,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationSpec,
    SummaryTable,
    ZoneMetrics,
)
from ecoloop_energyplus.infrastructure.execution.execution_result import ExecutionResult
from ecoloop_energyplus.infrastructure.locator import EnergyPlusInstallationCandidate
from ecoloop_energyplus.parser.csv.models import CsvParseResult
from ecoloop_energyplus.parser.err import ErrDiagnosticsReport
from ecoloop_energyplus.parser.eso.models import EsoParseResult
from ecoloop_energyplus.parser.sql.models import SqlParseResult
from ecoloop_energyplus.parser.summary.models import SummaryParseResult

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class SimulationResultAssembler:
    """Merge EnergyPlus execution and parser outputs into one result model."""

    def __init__(
        self,
        *,
        hostname_provider: Callable[[], str] | None = None,
    ) -> None:
        """Initialize the assembler with injectable platform metadata providers."""
        self._hostname_provider = hostname_provider or socket.gethostname

    def assemble(
        self,
        *,
        simulation_id: UUID,
        spec: SimulationSpec,
        candidate: EnergyPlusInstallationCandidate,
        execution_result: ExecutionResult,
        artifacts: tuple[SimulationArtifact, ...],
        err_report: ErrDiagnosticsReport | None = None,
        sql_result: SqlParseResult | None = None,
        csv_result: CsvParseResult | None = None,
        eso_result: EsoParseResult | None = None,
        summary_result: SummaryParseResult | None = None,
        additional_diagnostics: tuple[str, ...] = (),
        parse_error: OutputParseError | None = None,
    ) -> SimulationResult:
        """Assemble one immutable simulation result from normalized sub-results."""
        metrics = SimulationMetrics()
        for parser_metrics in (
            sql_result.metrics if sql_result is not None else None,
            csv_result.metrics if csv_result is not None else None,
            eso_result.metrics if eso_result is not None else None,
            summary_result.metrics if summary_result is not None else None,
        ):
            if parser_metrics is None:
                continue

            metrics = self._merge_metrics(metrics, parser_metrics)

        final_status = self._resolve_final_status(
            execution_status=execution_result.status,
            err_report=err_report,
            parse_error=parse_error,
        )
        diagnostics = self._build_diagnostics(
            execution_result=execution_result,
            err_report=err_report,
            sql_result=sql_result,
            csv_result=csv_result,
            eso_result=eso_result,
            summary_result=summary_result,
            additional_diagnostics=additional_diagnostics,
            parse_error=parse_error,
        )
        metadata = SimulationMetadata(
            energyplus_version=candidate.version,
            installation_root=candidate.root_path,
            command_line=execution_result.command_line,
            exit_code=execution_result.exit_code,
            duration_ms=execution_result.duration_ms,
            idf_checksum=self._find_input_checksum(artifacts, spec.idf_path.name),
            epw_checksum=self._find_input_checksum(artifacts, spec.epw_path.name),
            hostname=self._hostname_provider(),
            started_at=execution_result.started_at,
            completed_at=execution_result.completed_at,
        )
        return SimulationResult(
            simulation_id=simulation_id,
            final_status=final_status,
            metrics=metrics,
            artifacts=artifacts,
            diagnostics=diagnostics,
            metadata=metadata,
        )

    def _resolve_final_status(
        self,
        *,
        execution_status: SimulationStatus,
        err_report: ErrDiagnosticsReport | None,
        parse_error: OutputParseError | None,
    ) -> SimulationStatus:
        """Resolve the final result status after parser and ERR inspection."""
        if parse_error is not None:
            return SimulationStatus.PARSE_FAILED

        if execution_status is not SimulationStatus.SUCCEEDED:
            return execution_status

        if err_report is not None and err_report.fatal_count > 0:
            return SimulationStatus.FAILED

        return execution_status

    def _build_diagnostics(
        self,
        *,
        execution_result: ExecutionResult,
        err_report: ErrDiagnosticsReport | None,
        sql_result: SqlParseResult | None,
        csv_result: CsvParseResult | None,
        eso_result: EsoParseResult | None,
        summary_result: SummaryParseResult | None,
        additional_diagnostics: tuple[str, ...],
        parse_error: OutputParseError | None,
    ) -> tuple[str, ...]:
        """Merge all diagnostic streams into one ordered immutable tuple."""
        diagnostics = list(additional_diagnostics)
        diagnostics.extend(execution_result.diagnostics)

        for parser_result in (sql_result, csv_result, eso_result, summary_result):
            if parser_result is not None:
                diagnostics.extend(parser_result.diagnostics)

        if err_report is not None:
            diagnostics.extend(
                (
                    f"{diagnostic.severity.value.upper()} "
                    f"line {diagnostic.line_number}: {diagnostic.message}"
                )
                for diagnostic in err_report.diagnostics
            )

        if parse_error is not None:
            diagnostics.append(parse_error.message)

        return tuple(diagnostics)

    def _merge_metrics(
        self,
        current: SimulationMetrics,
        incoming: SimulationMetrics,
    ) -> SimulationMetrics:
        """Merge one metrics container into another while preserving source precedence."""
        merged_values = dict(current.values)
        for key, value in incoming.values.items():
            merged_values.setdefault(key, value)

        return SimulationMetrics(
            values=merged_values,
            energy=self._merge_optional_model(current.energy, incoming.energy),
            hvac=self._merge_optional_model(current.hvac, incoming.hvac),
            comfort=self._merge_optional_model(current.comfort, incoming.comfort),
            weather=self._merge_optional_model(current.weather, incoming.weather),
            zones=self._merge_zones(current.zones, incoming.zones),
            monthly_summary=self._merge_summary_tables(
                current.monthly_summary,
                incoming.monthly_summary,
            ),
            annual_summary=self._merge_summary_tables(
                current.annual_summary,
                incoming.annual_summary,
            ),
        )

    def _merge_optional_model(
        self,
        current: _ModelT | None,
        incoming: _ModelT | None,
    ) -> _ModelT | None:
        """Merge two optional pydantic models by filling missing fields from the fallback."""
        if current is None:
            return incoming

        if incoming is None:
            return current

        merged_values: dict[str, object] = {}
        for field_name in type(current).model_fields:
            current_value = getattr(current, field_name)
            merged_values[field_name] = (
                current_value if current_value is not None else getattr(incoming, field_name)
            )

        return type(current)(**merged_values)

    def _merge_zones(
        self,
        current: tuple[ZoneMetrics, ...],
        incoming: tuple[ZoneMetrics, ...],
    ) -> tuple[ZoneMetrics, ...]:
        """Merge per-zone metrics by zone name while preserving source precedence."""
        merged: dict[str, ZoneMetrics] = {zone.zone_name: zone for zone in current}
        for zone in incoming:
            existing = merged.get(zone.zone_name)
            merged[zone.zone_name] = self._merge_optional_model(existing, zone) or zone

        return tuple(merged[name] for name in sorted(merged))

    def _merge_summary_tables(
        self,
        current: tuple[SummaryTable, ...],
        incoming: tuple[SummaryTable, ...],
    ) -> tuple[SummaryTable, ...]:
        """Merge summary tables by stable report-name and table-name identity."""
        merged: dict[tuple[str, str | None], SummaryTable] = {
            (table.name, table.report_name): table for table in current
        }
        for table in incoming:
            merged.setdefault((table.name, table.report_name), table)

        return tuple(merged[key] for key in merged)

    def _find_input_checksum(
        self,
        artifacts: tuple[SimulationArtifact, ...],
        expected_name: str,
    ) -> str | None:
        """Find the checksum for one staged input artifact when available."""
        for artifact in artifacts:
            if artifact.kind is not SimulationArtifactKind.INPUT:
                continue

            if artifact.relative_path.name == expected_name:
                return artifact.checksum

        return None


__all__ = ["SimulationResultAssembler"]
