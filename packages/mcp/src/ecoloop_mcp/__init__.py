"""Framework-independent MCP tool platform for EcoLoop AI."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecoloop_mcp.dependencies import McpServerDependencies
    from ecoloop_mcp.errors import McpToolError
    from ecoloop_mcp.registry import (
        ToolRegistration,
        ToolRegistry,
        build_tool_registrations,
    )
    from ecoloop_mcp.server import create_mcp_server
    from ecoloop_mcp.tools import ComparisonResult, ZoneMetricsCollection

_EXPORTS: dict[str, tuple[str, str]] = {
    "ComparisonResult": ("ecoloop_mcp.tools", "ComparisonResult"),
    "McpServerDependencies": ("ecoloop_mcp.dependencies", "McpServerDependencies"),
    "McpToolError": ("ecoloop_mcp.errors", "McpToolError"),
    "ToolRegistration": ("ecoloop_mcp.registry", "ToolRegistration"),
    "ToolRegistry": ("ecoloop_mcp.registry", "ToolRegistry"),
    "ZoneMetricsCollection": ("ecoloop_mcp.tools", "ZoneMetricsCollection"),
    "build_tool_registrations": ("ecoloop_mcp.registry", "build_tool_registrations"),
    "create_mcp_server": ("ecoloop_mcp.server", "create_mcp_server"),
}

__all__ = [
    "ComparisonResult",
    "McpServerDependencies",
    "McpToolError",
    "ToolRegistration",
    "ToolRegistry",
    "ZoneMetricsCollection",
    "__version__",
    "build_tool_registrations",
    "create_mcp_server",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """Lazily resolve public exports to keep lightweight imports dependency-safe."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from error

    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return the stable public module surface for interactive inspection."""
    return sorted(__all__)
