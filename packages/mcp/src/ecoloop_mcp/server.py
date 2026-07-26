"""Official MCP server assembly for the EcoLoop EnergyPlus tool platform."""

from __future__ import annotations

from typing import Any

from mcp.server.lowlevel import Server

from ecoloop_mcp.dependencies import McpServerDependencies
from ecoloop_mcp.registry import ToolRegistry, build_tool_registrations
from mcp import types


def create_mcp_server(dependencies: McpServerDependencies) -> Server[object, object]:
    """Create a framework-independent MCP server for the EnergyPlus platform."""
    registry = ToolRegistry(build_tool_registrations(dependencies))
    server: Server[object, object] = Server(
        name="ecoloop-energyplus-mcp",
        version="0.1.0",
        instructions=(
            "Use these tools to validate and execute EnergyPlus simulations through "
            "EcoLoop AI's SimulationService."
        ),
    )

    async def list_tools_handler(request: types.ListToolsRequest) -> types.ServerResult:
        """Publish the complete set of registered EnergyPlus MCP tools."""
        del request
        return types.ServerResult(types.ListToolsResult(tools=registry.list_tools()))

    async def call_tool_handler(request: types.CallToolRequest) -> types.ServerResult:
        """Execute one EnergyPlus MCP tool through the shared registry."""
        arguments: dict[str, Any] = request.params.arguments or {}
        result = registry.call_tool(request.params.name, arguments)
        return types.ServerResult(result)

    server.request_handlers[types.ListToolsRequest] = list_tools_handler
    server.request_handlers[types.CallToolRequest] = call_tool_handler

    return server


__all__ = ["create_mcp_server"]
