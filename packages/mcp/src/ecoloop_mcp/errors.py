"""Framework-independent MCP error payload models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorCategory = Literal[
    "application",
    "configuration",
    "domain",
    "infrastructure",
    "protocol",
    "simulation",
    "unexpected",
    "validation",
]


class McpToolError(BaseModel):
    """Structured error payload returned in MCP tool error results."""

    model_config = ConfigDict(frozen=True)

    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    category: ErrorCategory
    details: dict[str, object] = Field(default_factory=dict)


__all__ = ["ErrorCategory", "McpToolError"]
