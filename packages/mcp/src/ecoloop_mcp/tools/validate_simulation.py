"""MCP tool registration for simulation preflight validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus import SimulationSpec, ValidationResult
from ecoloop_mcp.dependencies import McpServerDependencies
from ecoloop_mcp.registry import ToolRegistration


class ValidateSimulationInput(BaseModel):
    """Structured tool input for validation-only simulation checks."""

    model_config = ConfigDict(frozen=True)

    spec: SimulationSpec


def create_validate_simulation_tool(dependencies: McpServerDependencies) -> ToolRegistration:
    """Create the MCP registration for validation-only simulation checks."""

    def handler(payload: ValidateSimulationInput) -> ValidationResult:
        """Validate a simulation specification without executing EnergyPlus."""
        return dependencies.input_validator.validate(
            payload.spec,
            dependencies.simulation_settings,
        )

    return ToolRegistration(
        name="validate_simulation",
        title="Validate Simulation",
        description=(
            "Validate a simulation specification without executing EnergyPlus."
        ),
        input_model=ValidateSimulationInput,
        output_model=ValidationResult,
        handler=handler,
    )


__all__ = ["ValidateSimulationInput", "create_validate_simulation_tool"]
