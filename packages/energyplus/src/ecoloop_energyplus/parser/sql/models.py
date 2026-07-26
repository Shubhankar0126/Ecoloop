"""Typed SQL parser result models for EnergyPlus SQLite artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.domain.models import SimulationMetrics


class SqlParseResult(BaseModel):
    """Normalized SQL parsing output with derived metrics and counts."""

    model_config = ConfigDict(frozen=True)

    source: Path | None = None
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    summary_cell_count: int = Field(default=0, ge=0)
    time_series_row_count: int = Field(default=0, ge=0)
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def empty(
        cls,
        *,
        source: Path | None = None,
        diagnostics: tuple[str, ...] = (),
    ) -> SqlParseResult:
        """Build an empty SQL parse result."""
        return cls(source=source, diagnostics=diagnostics)


__all__ = ["SqlParseResult"]
