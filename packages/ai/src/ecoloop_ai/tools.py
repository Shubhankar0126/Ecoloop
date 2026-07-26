"""MCP-only tool access for the EcoLoop AI agent."""

from __future__ import annotations

from typing import Any, Protocol, cast

import anyio
from mcp.server.lowlevel import Server

from ecoloop_ai.models import AgentToolName, ToolCatalogEntry, ToolExecutionRecord
from ecoloop_common.exceptions import InfrastructureError
from ecoloop_energyplus import EnergyMetrics, SimulationResult, ValidationResult
from ecoloop_mcp import ComparisonResult, McpToolError, ZoneMetricsCollection
from mcp import types


class McpToolClient(Protocol):
    """Synchronous MCP tool client contract used by planner and nodes."""

    def list_tools(self) -> tuple[ToolCatalogEntry, ...]:
        """Discover the available MCP tool catalog."""

    def call_tool(
        self,
        tool_name: AgentToolName,
        arguments: dict[str, Any],
    ) -> ToolExecutionRecord:
        """Execute one MCP tool call and normalize the result."""


class InProcessMcpToolClient:
    """Invoke MCP tools through an in-process official SDK server instance."""

    def __init__(self, server: Server[object, object]) -> None:
        """Initialize the client with a compiled MCP server dependency."""
        self._server = server

    def list_tools(self) -> tuple[ToolCatalogEntry, ...]:
        """List tools by invoking the MCP `tools/list` handler."""
        response = anyio.run(self._list_tools_async)
        result = cast(types.ListToolsResult, response.root)
        return tuple(
            ToolCatalogEntry(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=tool.outputSchema or {},
            )
            for tool in result.tools
        )

    def call_tool(
        self,
        tool_name: AgentToolName,
        arguments: dict[str, Any],
    ) -> ToolExecutionRecord:
        """Execute one MCP tool call and capture structured success or failure."""
        response = anyio.run(
            self._call_tool_async,
            tool_name.value,
            arguments,
        )
        result = cast(types.CallToolResult, response.root)
        content_text = _first_text_content(result)
        structured_output = (
            result.structuredContent
            if isinstance(result.structuredContent, dict)
            else None
        )

        if result.isError:
            return ToolExecutionRecord(
                tool_name=tool_name.value,
                arguments=arguments,
                success=False,
                structured_output=structured_output,
                error=_coerce_tool_error(structured_output, content_text),
                content_text=content_text,
            )

        return ToolExecutionRecord(
            tool_name=tool_name.value,
            arguments=arguments,
            success=True,
            structured_output=structured_output,
            error=None,
            content_text=content_text,
        )

    async def _list_tools_async(self) -> types.ServerResult:
        """Call the low-level MCP `tools/list` handler asynchronously."""
        handler = self._server.request_handlers.get(types.ListToolsRequest)
        if handler is None:
            raise InfrastructureError("The MCP server does not expose a tools/list handler.")

        return await handler(types.ListToolsRequest())

    async def _call_tool_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> types.ServerResult:
        """Call the low-level MCP `tools/call` handler asynchronously."""
        handler = self._server.request_handlers.get(types.CallToolRequest)
        if handler is None:
            raise InfrastructureError("The MCP server does not expose a tools/call handler.")

        return await handler(
            types.CallToolRequest(
                params=types.CallToolRequestParams(
                    name=tool_name,
                    arguments=arguments,
                )
            )
        )


def parse_tool_output(record: ToolExecutionRecord) -> object | None:
    """Parse a successful tool record into its strongly typed domain model."""
    if not record.success or record.structured_output is None:
        return None

    try:
        tool_name = AgentToolName(record.tool_name)
    except ValueError:
        return None

    if tool_name is AgentToolName.SIMULATE_BUILDING:
        return SimulationResult.model_validate(record.structured_output)

    if tool_name is AgentToolName.COMPARE_SIMULATIONS:
        return ComparisonResult.model_validate(record.structured_output)

    if tool_name is AgentToolName.GET_ENERGY_METRICS:
        return EnergyMetrics.model_validate(record.structured_output)

    if tool_name is AgentToolName.GET_ZONE_METRICS:
        return ZoneMetricsCollection.model_validate(record.structured_output)

    return ValidationResult.model_validate(record.structured_output)


def _first_text_content(result: types.CallToolResult) -> str | None:
    """Extract the first text block from an MCP tool result."""
    for block in result.content:
        if isinstance(block, types.TextContent):
            return block.text

    return None


def _coerce_tool_error(
    structured_output: dict[str, Any] | None,
    content_text: str | None,
) -> McpToolError:
    """Create a typed MCP error model from structured or textual tool failures."""
    if structured_output is not None:
        return McpToolError.model_validate(structured_output)

    return McpToolError(
        error_code="mcp.unknown_error",
        message=content_text or "The MCP tool failed without a structured error payload.",
        category="unexpected",
        details={},
    )


__all__ = ["InProcessMcpToolClient", "McpToolClient", "parse_tool_output"]
