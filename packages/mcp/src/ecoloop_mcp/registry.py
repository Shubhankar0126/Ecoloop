"""Modular MCP tool registration and typed result adaptation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from ecoloop_common.exceptions import (
    ApplicationError,
    ConfigurationError,
    DomainError,
    EcoLoopError,
    InfrastructureError,
)
from ecoloop_common.exceptions import ValidationError as EcoLoopValidationError
from ecoloop_energyplus.domain.exceptions import (
    EnergyPlusConfigurationError,
    InvalidSimulationInput,
    OutputParseError,
    SimulationError,
)
from ecoloop_mcp.dependencies import McpServerDependencies
from ecoloop_mcp.errors import ErrorCategory, McpToolError
from mcp import types


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    """Declarative MCP tool metadata and execution contract."""

    name: str
    title: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[Any], object]
    annotations: types.ToolAnnotations | None = None

    def as_mcp_tool(self) -> types.Tool:
        """Convert the registration into an MCP tool definition."""
        return types.Tool(
            name=self.name,
            title=self.title,
            description=self.description,
            inputSchema=self.input_model.model_json_schema(),
            outputSchema=self.output_model.model_json_schema(),
            annotations=self.annotations,
        )


class ToolRegistry:
    """Own tool definitions, input validation, and MCP result serialization."""

    def __init__(self, registrations: Iterable[ToolRegistration]) -> None:
        """Initialize the registry and reject duplicate tool names eagerly."""
        registration_map: dict[str, ToolRegistration] = {}
        for registration in registrations:
            if registration.name in registration_map:
                raise ValueError(f"Duplicate MCP tool registration: {registration.name}.")

            registration_map[registration.name] = registration

        self._registrations = registration_map

    def list_tools(self) -> list[types.Tool]:
        """Return MCP tool definitions for client discovery."""
        return [
            registration.as_mcp_tool()
            for registration in self._registrations.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        """Validate, execute, and serialize one tool call into an MCP result."""
        registration = self._registrations.get(name)
        if registration is None:
            return self._error_result(
                McpToolError(
                    error_code="mcp.tool_not_found",
                    message=f"Unknown MCP tool: {name}.",
                    category="protocol",
                    details={"tool_name": name},
                )
            )

        try:
            validated_arguments = registration.input_model.model_validate(arguments)
        except ValidationError as error:
            return self._error_result(self._map_argument_validation_error(error))

        try:
            raw_result = registration.handler(validated_arguments)
            validated_result = registration.output_model.model_validate(raw_result)
        except EcoLoopError as error:
            return self._error_result(self._map_ecoloop_error(error))
        except ValidationError as error:
            return self._error_result(self._map_output_validation_error(error))
        except Exception as error:
            return self._error_result(
                McpToolError(
                    error_code="ecoloop.unexpected_error",
                    message="An unexpected MCP tool error occurred.",
                    category="unexpected",
                    details={"exception_type": type(error).__name__},
                )
            )

        return self._success_result(validated_result)

    @staticmethod
    def _success_result(result: BaseModel) -> types.CallToolResult:
        """Build a successful MCP tool result with structured JSON content."""
        structured_content = result.model_dump(mode="json")
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2),
                )
            ],
            structuredContent=structured_content,
            isError=False,
        )

    @staticmethod
    def _error_result(error: McpToolError) -> types.CallToolResult:
        """Build a structured MCP tool error result."""
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=error.model_dump_json(indent=2),
                )
            ],
            structuredContent=error.model_dump(mode="json"),
            isError=True,
        )

    def _map_argument_validation_error(self, error: ValidationError) -> McpToolError:
        """Map malformed tool arguments into a typed protocol-level error payload."""
        return McpToolError(
            error_code="mcp.invalid_arguments",
            message="Tool arguments failed validation.",
            category="protocol",
            details={"errors": self._serialize_validation_errors(error)},
        )

    def _map_output_validation_error(self, error: ValidationError) -> McpToolError:
        """Map invalid tool return payloads into a typed internal error payload."""
        return McpToolError(
            error_code="mcp.invalid_tool_output",
            message="Tool output failed validation.",
            category="unexpected",
            details={"errors": self._serialize_validation_errors(error)},
        )

    def _map_ecoloop_error(self, error: EcoLoopError) -> McpToolError:
        """Map shared EcoLoop exceptions into structured MCP tool errors."""
        return McpToolError(
            error_code=error.error_code,
            message=error.message,
            category=self._categorize_error(error),
            details=error.as_dict(),
        )

    @staticmethod
    def _serialize_validation_errors(error: ValidationError) -> list[dict[str, object]]:
        """Serialize Pydantic validation details into JSON-safe error metadata."""
        return [
            {
                "location": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors(include_url=False)
        ]

    @staticmethod
    def _categorize_error(error: EcoLoopError) -> ErrorCategory:
        """Assign a stable error category for shared exception families."""
        if isinstance(error, InvalidSimulationInput | EcoLoopValidationError):
            return "validation"

        if isinstance(error, EnergyPlusConfigurationError | ConfigurationError):
            return "configuration"

        if isinstance(error, SimulationError | OutputParseError):
            return "simulation"

        if isinstance(error, InfrastructureError):
            return "infrastructure"

        if isinstance(error, ApplicationError):
            return "application"

        if isinstance(error, DomainError):
            return "domain"

        return "unexpected"


def build_tool_registrations(
    dependencies: McpServerDependencies,
) -> tuple[ToolRegistration, ...]:
    """Create the complete EcoLoop MCP tool set for one dependency graph."""
    from ecoloop_mcp.tools import (
        create_compare_simulations_tool,
        create_get_energy_metrics_tool,
        create_get_zone_metrics_tool,
        create_simulate_building_tool,
        create_validate_simulation_tool,
    )

    return (
        create_simulate_building_tool(dependencies),
        create_compare_simulations_tool(),
        create_get_energy_metrics_tool(),
        create_get_zone_metrics_tool(),
        create_validate_simulation_tool(dependencies),
    )


__all__ = [
    "McpToolError",
    "ToolRegistration",
    "ToolRegistry",
    "build_tool_registrations",
]
