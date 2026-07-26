"""Metric abstractions and lookup helpers shared by optimization modules."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus import SimulationMetrics


class OptimizationMetricTrend(StrEnum):
    """Normalized interpretation of how one metric moved across candidates."""

    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class OptimizationMetricSnapshot(BaseModel):
    """A parser-agnostic metric snapshot used by the optimization foundation."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    baseline_value: float | None = None
    candidate_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    trend: OptimizationMetricTrend = OptimizationMetricTrend.UNKNOWN

    def delta(self) -> float | None:
        """Return the candidate-to-baseline delta when both values are available."""
        if self.baseline_value is None or self.candidate_value is None:
            return None

        return self.candidate_value - self.baseline_value


_STRUCTURED_METRIC_PATHS: dict[str, tuple[str, str]] = {
    "total_site_energy_kwh": ("energy", "total_site_energy_kwh"),
    "electricity_consumption_kwh": ("energy", "electricity_consumption_kwh"),
    "heating_energy_kwh": ("hvac", "heating_energy_kwh"),
    "cooling_energy_kwh": ("hvac", "cooling_energy_kwh"),
    "hvac_energy_kwh": ("hvac", "hvac_energy_kwh"),
    "equipment_loads_kwh": ("hvac", "equipment_loads_kwh"),
    "average_zone_temperature_celsius": ("comfort", "average_zone_temperature_celsius"),
    "average_zone_humidity_percent": ("comfort", "average_zone_humidity_percent"),
    "average_pmv": ("comfort", "average_pmv"),
    "average_ppd_percent": ("comfort", "average_ppd_percent"),
    "average_outdoor_dry_bulb_celsius": ("weather", "average_outdoor_dry_bulb_celsius"),
    "average_outdoor_relative_humidity_percent": (
        "weather",
        "average_outdoor_relative_humidity_percent",
    ),
}


def resolve_metric_value(metrics: SimulationMetrics, metric_name: str) -> float | None:
    """Resolve a numeric metric value from normalized simulation metrics."""
    path = _STRUCTURED_METRIC_PATHS.get(metric_name)
    if path is not None:
        container = getattr(metrics, path[0])
        if container is not None:
            value = getattr(container, path[1])
            if isinstance(value, int | float) and not isinstance(value, bool):
                return float(value)

    metric_value = metrics.values.get(metric_name)
    if metric_value is None:
        return None

    value = metric_value.value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)

    return None


def resolve_metric_unit(metrics: SimulationMetrics, metric_name: str) -> str | None:
    """Resolve a metric unit from either structured or generic simulation metrics."""
    metric_value = metrics.values.get(metric_name)
    if metric_value is not None and metric_value.unit is not None:
        return metric_value.unit

    if metric_name.endswith("_kwh"):
        return "kWh"

    if metric_name.endswith("_kw"):
        return "kW"

    if metric_name.endswith("_usd"):
        return "USD"

    if metric_name.endswith("_kgco2e"):
        return "kgCO2e"

    if metric_name.endswith("_percent"):
        return "%"

    if metric_name.endswith("_celsius"):
        return "C"

    return None


__all__ = [
    "OptimizationMetricSnapshot",
    "OptimizationMetricTrend",
    "resolve_metric_unit",
    "resolve_metric_value",
]
