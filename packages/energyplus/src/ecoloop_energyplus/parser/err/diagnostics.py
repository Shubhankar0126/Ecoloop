"""Normalized diagnostic models parsed from ``eplusout.err`` files."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.parser.err.severity import ErrSeverity


class ErrDiagnostic(BaseModel):
    """One normalized ERR diagnostic entry."""

    model_config = ConfigDict(frozen=True)

    severity: ErrSeverity
    message: str = Field(min_length=1)
    line_number: int = Field(ge=1)
    raw_line: str = Field(min_length=1)


class ErrDiagnosticsReport(BaseModel):
    """Aggregated ERR diagnostics extracted from one source file or text blob."""

    model_config = ConfigDict(frozen=True)

    source: Path | None = None
    diagnostics: tuple[ErrDiagnostic, ...] = ()
    fatal_count: int = Field(default=0, ge=0)
    severe_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: tuple[ErrDiagnostic, ...],
        *,
        source: Path | None = None,
    ) -> ErrDiagnosticsReport:
        """Build a report with normalized severity counts."""
        return cls(
            source=source,
            diagnostics=diagnostics,
            fatal_count=sum(
                1 for diagnostic in diagnostics if diagnostic.severity is ErrSeverity.FATAL
            ),
            severe_count=sum(
                1 for diagnostic in diagnostics if diagnostic.severity is ErrSeverity.SEVERE
            ),
            warning_count=sum(
                1 for diagnostic in diagnostics if diagnostic.severity is ErrSeverity.WARNING
            ),
        )


__all__ = ["ErrDiagnostic", "ErrDiagnosticsReport"]
