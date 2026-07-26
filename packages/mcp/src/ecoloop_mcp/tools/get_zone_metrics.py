"""MCP tool registration for extracting normalized zone metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus import SimulationResult, ZoneMetrics
from ecoloop_mcp.registry import ToolRegistration


class GetZoneMetricsInput(BaseModel):
    """Structured tool input for zone metric extraction."""

    model_config = ConfigDict(frozen=True)

    result: SimulationResult


class ZoneMetricsCollection(BaseModel):
    """A typed collection of normalized zone metrics."""

    model_config = ConfigDict(frozen=True)

    zones: tuple[ZoneMetrics, ...] = ()


def create_get_zone_metrics_tool() -> ToolRegistration:
    """Create the MCP registration for returning only zone metrics."""

    def handler(payload: GetZoneMetricsInput) -> ZoneMetricsCollection:
        """Extract per-zone metrics from one simulation result."""
        return ZoneMetricsCollection(zones=payload.result.metrics.zones)

    return ToolRegistration(
        name="get_zone_metrics",
        title="Get Zone Metrics",
        description="Extract normalized zone metrics from a simulation result.",
        input_model=GetZoneMetricsInput,
        output_model=ZoneMetricsCollection,
        handler=handler,
    )


__all__ = [
    "GetZoneMetricsInput",
    "ZoneMetricsCollection",
    "create_get_zone_metrics_tool",
]
