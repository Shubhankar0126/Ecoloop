"""Typed ESO parser result models for EnergyPlus output artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus.domain.models import SimulationMetrics


class EsoVariableDefinition(BaseModel):
    """One variable definition extracted from an EnergyPlus ESO dictionary."""

    model_config = ConfigDict(frozen=True)

    record_id: int = Field(ge=1)
    key: str | None = None
    name: str = Field(min_length=1)
    unit: str | None = None
    frequency: str | None = None


class EsoSeries(BaseModel):
    """One normalized ESO series with its originating variable definition."""

    model_config = ConfigDict(frozen=True)

    definition: EsoVariableDefinition
    values: tuple[float, ...] = ()


class EsoParseResult(BaseModel):
    """Normalized ESO parsing output with derived metrics and raw series schema."""

    model_config = ConfigDict(frozen=True)

    source: Path | None = None
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    variables: tuple[EsoVariableDefinition, ...] = ()
    series: tuple[EsoSeries, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def empty(
        cls,
        *,
        source: Path | None = None,
        diagnostics: tuple[str, ...] = (),
    ) -> EsoParseResult:
        """Build an empty ESO parse result."""
        return cls(source=source, diagnostics=diagnostics)


__all__ = [
    "EsoParseResult",
    "EsoSeries",
    "EsoVariableDefinition",
]
