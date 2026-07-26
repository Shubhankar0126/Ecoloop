"""Dependency contracts for the EcoLoop MCP server package."""

from __future__ import annotations

from dataclasses import dataclass

from ecoloop_energyplus import InputValidator, SimulationService, SimulationSettings


@dataclass(frozen=True, slots=True)
class McpServerDependencies:
    """Injected framework-independent dependencies required by MCP tools."""

    simulation_service: SimulationService
    input_validator: InputValidator
    simulation_settings: SimulationSettings


__all__ = ["McpServerDependencies"]
