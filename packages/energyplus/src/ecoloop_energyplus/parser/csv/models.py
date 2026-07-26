"""Typed CSV parser result models for EnergyPlus time-series artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.domain.models import SimulationMetrics


class CsvColumn(BaseModel):
    """A normalized EnergyPlus CSV column definition."""

    model_config = ConfigDict(frozen=True)

    raw_name: str = Field(min_length=1)
    name: str = Field(min_length=1)
    key: str | None = None
    unit: str | None = None
    frequency: str | None = None


class CsvParseResult(BaseModel):
    """Normalized CSV parsing output with derived metrics and schema details."""

    model_config = ConfigDict(frozen=True)

    source: Path | None = None
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    columns: tuple[CsvColumn, ...] = ()
    row_count: int = Field(default=0, ge=0)
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def empty(
        cls,
        *,
        source: Path | None = None,
        diagnostics: tuple[str, ...] = (),
    ) -> CsvParseResult:
        """Build an empty CSV parse result."""
        return cls(source=source, diagnostics=diagnostics)


__all__ = [
    "CsvColumn",
    "CsvParseResult",
]
