"""MCP tool registration for extracting normalized energy metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus import EnergyMetrics, SimulationResult
from ecoloop_mcp.registry import ToolRegistration


class GetEnergyMetricsInput(BaseModel):
    """Structured tool input for energy metric extraction."""

    model_config = ConfigDict(frozen=True)

    result: SimulationResult


def create_get_energy_metrics_tool() -> ToolRegistration:
    """Create the MCP registration for returning only EnergyMetrics."""

    def handler(payload: GetEnergyMetricsInput) -> EnergyMetrics:
        """Extract building-level energy metrics from one simulation result."""
        return payload.result.metrics.energy or EnergyMetrics()

    return ToolRegistration(
        name="get_energy_metrics",
        title="Get Energy Metrics",
        description="Extract only normalized energy metrics from a simulation result.",
        input_model=GetEnergyMetricsInput,
        output_model=EnergyMetrics,
        handler=handler,
    )


__all__ = ["GetEnergyMetricsInput", "create_get_energy_metrics_tool"]
