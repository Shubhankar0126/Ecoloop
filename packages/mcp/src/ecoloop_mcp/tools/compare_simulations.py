"""MCP tool registration for comparing two normalized simulation results."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus import SimulationResult
from ecoloop_mcp.registry import ToolRegistration


class CompareSimulationsInput(BaseModel):
    """Structured tool input for comparing two completed simulations."""

    model_config = ConfigDict(frozen=True)

    baseline: SimulationResult
    candidate: SimulationResult


class MetricDelta(BaseModel):
    """A normalized numeric delta between a baseline and candidate metric."""

    model_config = ConfigDict(frozen=True)

    baseline: float | None = None
    candidate: float | None = None
    delta: float | None = None


class EnergyDifference(BaseModel):
    """Energy-focused differences between two simulation results."""

    model_config = ConfigDict(frozen=True)

    total_site_energy_kwh: MetricDelta = MetricDelta()
    electricity_consumption_kwh: MetricDelta = MetricDelta()


class HVACDifference(BaseModel):
    """HVAC-focused differences between two simulation results."""

    model_config = ConfigDict(frozen=True)

    heating_energy_kwh: MetricDelta = MetricDelta()
    cooling_energy_kwh: MetricDelta = MetricDelta()
    hvac_energy_kwh: MetricDelta = MetricDelta()
    equipment_loads_kwh: MetricDelta = MetricDelta()


class ComfortDifference(BaseModel):
    """Comfort-focused differences between two simulation results."""

    model_config = ConfigDict(frozen=True)

    average_zone_temperature_celsius: MetricDelta = MetricDelta()
    average_zone_humidity_percent: MetricDelta = MetricDelta()
    average_pmv: MetricDelta = MetricDelta()
    average_ppd_percent: MetricDelta = MetricDelta()


class WeatherDifference(BaseModel):
    """Weather-focused differences between two simulation results."""

    model_config = ConfigDict(frozen=True)

    average_outdoor_dry_bulb_celsius: MetricDelta = MetricDelta()
    average_outdoor_relative_humidity_percent: MetricDelta = MetricDelta()


class ComparisonResult(BaseModel):
    """Normalized comparison payload returned to MCP callers."""

    model_config = ConfigDict(frozen=True)

    baseline_simulation_id: UUID
    candidate_simulation_id: UUID
    energy: EnergyDifference
    hvac: HVACDifference
    comfort: ComfortDifference
    weather: WeatherDifference


def create_compare_simulations_tool() -> ToolRegistration:
    """Create the MCP registration for simulation comparison."""

    def handler(payload: CompareSimulationsInput) -> ComparisonResult:
        """Compare two normalized simulation results field by field."""
        baseline_metrics = payload.baseline.metrics
        candidate_metrics = payload.candidate.metrics
        baseline_energy = baseline_metrics.energy
        candidate_energy = candidate_metrics.energy
        baseline_hvac = baseline_metrics.hvac
        candidate_hvac = candidate_metrics.hvac
        baseline_comfort = baseline_metrics.comfort
        candidate_comfort = candidate_metrics.comfort
        baseline_weather = baseline_metrics.weather
        candidate_weather = candidate_metrics.weather

        return ComparisonResult(
            baseline_simulation_id=payload.baseline.simulation_id,
            candidate_simulation_id=payload.candidate.simulation_id,
            energy=EnergyDifference(
                total_site_energy_kwh=_delta(
                    _optional_float(
                        None if baseline_energy is None else baseline_energy.total_site_energy_kwh
                    ),
                    _optional_float(
                        None
                        if candidate_energy is None
                        else candidate_energy.total_site_energy_kwh
                    ),
                ),
                electricity_consumption_kwh=_delta(
                    _optional_float(
                        None
                        if baseline_energy is None
                        else baseline_energy.electricity_consumption_kwh
                    ),
                    _optional_float(
                        None
                        if candidate_energy is None
                        else candidate_energy.electricity_consumption_kwh
                    ),
                ),
            ),
            hvac=HVACDifference(
                heating_energy_kwh=_delta(
                    _optional_float(
                        None if baseline_hvac is None else baseline_hvac.heating_energy_kwh
                    ),
                    _optional_float(
                        None if candidate_hvac is None else candidate_hvac.heating_energy_kwh
                    ),
                ),
                cooling_energy_kwh=_delta(
                    _optional_float(
                        None if baseline_hvac is None else baseline_hvac.cooling_energy_kwh
                    ),
                    _optional_float(
                        None if candidate_hvac is None else candidate_hvac.cooling_energy_kwh
                    ),
                ),
                hvac_energy_kwh=_delta(
                    _optional_float(
                        None if baseline_hvac is None else baseline_hvac.hvac_energy_kwh
                    ),
                    _optional_float(
                        None if candidate_hvac is None else candidate_hvac.hvac_energy_kwh
                    ),
                ),
                equipment_loads_kwh=_delta(
                    _optional_float(
                        None if baseline_hvac is None else baseline_hvac.equipment_loads_kwh
                    ),
                    _optional_float(
                        None if candidate_hvac is None else candidate_hvac.equipment_loads_kwh
                    ),
                ),
            ),
            comfort=ComfortDifference(
                average_zone_temperature_celsius=_delta(
                    _optional_float(
                        None
                        if baseline_comfort is None
                        else baseline_comfort.average_zone_temperature_celsius
                    ),
                    _optional_float(
                        None
                        if candidate_comfort is None
                        else candidate_comfort.average_zone_temperature_celsius
                    ),
                ),
                average_zone_humidity_percent=_delta(
                    _optional_float(
                        None
                        if baseline_comfort is None
                        else baseline_comfort.average_zone_humidity_percent
                    ),
                    _optional_float(
                        None
                        if candidate_comfort is None
                        else candidate_comfort.average_zone_humidity_percent
                    ),
                ),
                average_pmv=_delta(
                    _optional_float(
                        None if baseline_comfort is None else baseline_comfort.average_pmv
                    ),
                    _optional_float(
                        None if candidate_comfort is None else candidate_comfort.average_pmv
                    ),
                ),
                average_ppd_percent=_delta(
                    _optional_float(
                        None if baseline_comfort is None else baseline_comfort.average_ppd_percent
                    ),
                    _optional_float(
                        None if candidate_comfort is None else candidate_comfort.average_ppd_percent
                    ),
                ),
            ),
            weather=WeatherDifference(
                average_outdoor_dry_bulb_celsius=_delta(
                    _optional_float(
                        None
                        if baseline_weather is None
                        else baseline_weather.average_outdoor_dry_bulb_celsius
                    ),
                    _optional_float(
                        None
                        if candidate_weather is None
                        else candidate_weather.average_outdoor_dry_bulb_celsius
                    ),
                ),
                average_outdoor_relative_humidity_percent=_delta(
                    _optional_float(
                        None
                        if baseline_weather is None
                        else baseline_weather.average_outdoor_relative_humidity_percent
                    ),
                    _optional_float(
                        None
                        if candidate_weather is None
                        else candidate_weather.average_outdoor_relative_humidity_percent
                    ),
                ),
            ),
        )

    return ToolRegistration(
        name="compare_simulations",
        title="Compare Simulations",
        description=(
            "Compare two simulation results and report normalized energy, HVAC, "
            "comfort, and weather deltas."
        ),
        input_model=CompareSimulationsInput,
        output_model=ComparisonResult,
        handler=handler,
    )


def _delta(baseline: float | None, candidate: float | None) -> MetricDelta:
    """Build one normalized numeric delta payload."""
    if baseline is None or candidate is None:
        return MetricDelta(baseline=baseline, candidate=candidate, delta=None)

    return MetricDelta(
        baseline=baseline,
        candidate=candidate,
        delta=candidate - baseline,
    )


def _optional_float(value: float | int | None) -> float | None:
    """Normalize numeric values to floats while preserving missing metrics."""
    if value is None:
        return None

    return float(value)


__all__ = [
    "ComfortDifference",
    "CompareSimulationsInput",
    "ComparisonResult",
    "EnergyDifference",
    "HVACDifference",
    "MetricDelta",
    "WeatherDifference",
    "create_compare_simulations_tool",
]
