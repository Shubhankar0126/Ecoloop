"""Framework-independent AI agent platform for EcoLoop AI."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecoloop_ai.agent import AgentRunResult, EcoLoopAgent
    from ecoloop_ai.config import AgentLoopSettings, AiAgentConfig, OllamaSettings
    from ecoloop_ai.memory import AgentMemory, AgentMemoryManager
    from ecoloop_ai.models import (
        AgentMessage,
        AgentRequest,
        AgentToolName,
        AnalysisResult,
        BuildingContext,
        ConversationRole,
        ConversationTurn,
        CriticResult,
        OptimizationReport,
        PlannedToolCall,
        PlannerDecision,
        PlanStep,
        PreviousOptimization,
        SimulationHistoryEntry,
        ToolCatalogEntry,
        ToolExecutionRecord,
        UserGoal,
    )
    from ecoloop_ai.prompts import PromptLibrary
    from ecoloop_ai.state import AgentState
    from ecoloop_ai.tools import InProcessMcpToolClient, McpToolClient, parse_tool_output

_EXPORTS: dict[str, tuple[str, str]] = {
    "AgentLoopSettings": ("ecoloop_ai.config", "AgentLoopSettings"),
    "AgentMemory": ("ecoloop_ai.memory", "AgentMemory"),
    "AgentMemoryManager": ("ecoloop_ai.memory", "AgentMemoryManager"),
    "AgentMessage": ("ecoloop_ai.models", "AgentMessage"),
    "AgentRequest": ("ecoloop_ai.models", "AgentRequest"),
    "AgentRunResult": ("ecoloop_ai.agent", "AgentRunResult"),
    "AgentState": ("ecoloop_ai.state", "AgentState"),
    "AgentToolName": ("ecoloop_ai.models", "AgentToolName"),
    "AiAgentConfig": ("ecoloop_ai.config", "AiAgentConfig"),
    "AnalysisResult": ("ecoloop_ai.models", "AnalysisResult"),
    "BuildingContext": ("ecoloop_ai.models", "BuildingContext"),
    "ConversationRole": ("ecoloop_ai.models", "ConversationRole"),
    "ConversationTurn": ("ecoloop_ai.models", "ConversationTurn"),
    "CriticResult": ("ecoloop_ai.models", "CriticResult"),
    "EcoLoopAgent": ("ecoloop_ai.agent", "EcoLoopAgent"),
    "InProcessMcpToolClient": ("ecoloop_ai.tools", "InProcessMcpToolClient"),
    "McpToolClient": ("ecoloop_ai.tools", "McpToolClient"),
    "OllamaSettings": ("ecoloop_ai.config", "OllamaSettings"),
    "OptimizationReport": ("ecoloop_ai.models", "OptimizationReport"),
    "PlanStep": ("ecoloop_ai.models", "PlanStep"),
    "PlannedToolCall": ("ecoloop_ai.models", "PlannedToolCall"),
    "PlannerDecision": ("ecoloop_ai.models", "PlannerDecision"),
    "PreviousOptimization": ("ecoloop_ai.models", "PreviousOptimization"),
    "PromptLibrary": ("ecoloop_ai.prompts", "PromptLibrary"),
    "SimulationHistoryEntry": ("ecoloop_ai.models", "SimulationHistoryEntry"),
    "ToolCatalogEntry": ("ecoloop_ai.models", "ToolCatalogEntry"),
    "ToolExecutionRecord": ("ecoloop_ai.models", "ToolExecutionRecord"),
    "UserGoal": ("ecoloop_ai.models", "UserGoal"),
    "parse_tool_output": ("ecoloop_ai.tools", "parse_tool_output"),
}

__all__ = [
    "AgentLoopSettings",
    "AgentMemory",
    "AgentMemoryManager",
    "AgentMessage",
    "AgentRequest",
    "AgentRunResult",
    "AgentState",
    "AgentToolName",
    "AiAgentConfig",
    "AnalysisResult",
    "BuildingContext",
    "ConversationRole",
    "ConversationTurn",
    "CriticResult",
    "EcoLoopAgent",
    "InProcessMcpToolClient",
    "McpToolClient",
    "OllamaSettings",
    "OptimizationReport",
    "PlanStep",
    "PlannedToolCall",
    "PlannerDecision",
    "PreviousOptimization",
    "PromptLibrary",
    "SimulationHistoryEntry",
    "ToolCatalogEntry",
    "ToolExecutionRecord",
    "UserGoal",
    "__version__",
    "parse_tool_output",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """Lazily resolve public exports to avoid importing optional runtime stacks eagerly."""
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
