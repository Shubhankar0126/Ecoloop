"""MCP tool registration for running one EnergyPlus simulation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus import SimulationResult, SimulationSpec
from ecoloop_mcp.dependencies import McpServerDependencies
from ecoloop_mcp.registry import ToolRegistration


class SimulateBuildingInput(BaseModel):
    """Structured tool input for launching one building simulation."""

    model_config = ConfigDict(frozen=True)

    spec: SimulationSpec


def create_simulate_building_tool(dependencies: McpServerDependencies) -> ToolRegistration:
    """Create the MCP registration for the simulation execution entry point."""

    def handler(payload: SimulateBuildingInput) -> SimulationResult:
        """Execute one validated EnergyPlus simulation through the shared service."""
        return dependencies.simulation_service.run(payload.spec)

    return ToolRegistration(
        name="simulate_building",
        title="Simulate Building",
        description="Run one EnergyPlus simulation and return the normalized result.",
        input_model=SimulateBuildingInput,
        output_model=SimulationResult,
        handler=handler,
    )


__all__ = ["SimulateBuildingInput", "create_simulate_building_tool"]
