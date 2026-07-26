"""Typed summary parser result models for EnergyPlus output artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.domain.models import SimulationMetrics, SummaryTable


class SummaryParseResult(BaseModel):
    """Normalized summary parsing output with reusable domain tables."""

    model_config = ConfigDict(frozen=True)

    source: Path | None = None
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    tables: tuple[SummaryTable, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def empty(
        cls,
        *,
        source: Path | None = None,
        diagnostics: tuple[str, ...] = (),
    ) -> SummaryParseResult:
        """Build an empty summary parse result."""
        return cls(source=source, diagnostics=diagnostics)


__all__ = ["SummaryParseResult"]
