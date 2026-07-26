"""Shared data models for the EcoLoop AI agent package."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_energyplus import SimulationResult, SimulationSpec
from ecoloop_mcp import McpToolError


class ConversationRole(StrEnum):
    """Supported conversation roles tracked by the agent."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageKind(StrEnum):
    """Internal agent message categories captured in state."""

    PLAN = "plan"
    TOOL = "tool"
    ANALYSIS = "analysis"
    CRITIQUE = "critique"
    REPORT = "report"


class AgentToolName(StrEnum):
    """The only MCP tools the agent is allowed to call."""

    SIMULATE_BUILDING = "simulate_building"
    COMPARE_SIMULATIONS = "compare_simulations"
    GET_ENERGY_METRICS = "get_energy_metrics"
    GET_ZONE_METRICS = "get_zone_metrics"
    VALIDATE_SIMULATION = "validate_simulation"


class ConversationTurn(BaseModel):
    """One user-visible conversation turn captured by the agent."""

    model_config = ConfigDict(frozen=True)

    role: ConversationRole
    content: str = Field(min_length=1)


class AgentMessage(BaseModel):
    """One internal agent reasoning message stored in state."""

    model_config = ConfigDict(frozen=True)

    kind: MessageKind
    content: str = Field(min_length=1)


class UserGoal(BaseModel):
    """The optimization objective and measurable success criteria."""

    model_config = ConfigDict(frozen=True)

    objective: str = Field(min_length=1)
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    target_metrics: dict[str, float] = Field(default_factory=dict)


class BuildingContext(BaseModel):
    """Reusable building-specific context made available to the agent."""

    model_config = ConfigDict(frozen=True)

    building_name: str | None = None
    available_simulations: dict[str, SimulationSpec] = Field(default_factory=dict)
    current_simulation_key: str | None = None
    notes: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


class PreviousOptimization(BaseModel):
    """A historical optimization attempt available to agent memory."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    recommendations: tuple[str, ...] = ()


class PlanStep(BaseModel):
    """One high-level step in the current optimization plan."""

    model_config = ConfigDict(frozen=True)

    description: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)


class PlannedToolCall(BaseModel):
    """A single MCP tool invocation selected by the planner."""

    model_config = ConfigDict(frozen=True)

    tool_name: AgentToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1)


class PlannerDecision(BaseModel):
    """Structured planner output used by the LangGraph loop."""

    model_config = ConfigDict(frozen=True)

    plan_summary: str = Field(min_length=1)
    steps: tuple[PlanStep, ...] = ()
    selected_tool: PlannedToolCall
    expected_outcome: str = Field(min_length=1)


class ToolCatalogEntry(BaseModel):
    """A discovered MCP tool definition exposed to the planner."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRecord(BaseModel):
    """Normalized record of one MCP tool call."""

    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    success: bool
    structured_output: dict[str, Any] | None = None
    error: McpToolError | None = None
    content_text: str | None = None


class SimulationHistoryEntry(BaseModel):
    """A simulation execution and its latest assessment."""

    model_config = ConfigDict(frozen=True)

    simulation_result: SimulationResult
    analysis_summary: str | None = None
    goal_achieved: bool | None = None


class AnalysisResult(BaseModel):
    """Structured analysis of the latest tool execution and simulation state."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    goal_achieved: bool
    findings: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()


class CriticResult(BaseModel):
    """Structured critique that improves the next planning iteration."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    improvement_hypotheses: tuple[str, ...] = ()
    revised_focus: tuple[str, ...] = ()


class OptimizationReport(BaseModel):
    """Final user-facing report produced when the graph terminates."""

    model_config = ConfigDict(frozen=True)

    executive_summary: str = Field(min_length=1)
    goal_achieved: bool
    iterations_used: int = Field(ge=0)
    key_findings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()


class AgentRequest(BaseModel):
    """Public input contract for one AI agent run."""

    model_config = ConfigDict(frozen=True)

    goal: UserGoal
    conversation: tuple[ConversationTurn, ...] = ()
    building_context: BuildingContext | None = None
    previous_optimizations: tuple[PreviousOptimization, ...] = ()
    max_iterations: int | None = Field(default=None, ge=1, le=20)


__all__ = [
    "AgentMessage",
    "AgentRequest",
    "AgentToolName",
    "AnalysisResult",
    "BuildingContext",
    "ConversationRole",
    "ConversationTurn",
    "CriticResult",
    "MessageKind",
    "OptimizationReport",
    "PlanStep",
    "PlannedToolCall",
    "PlannerDecision",
    "PreviousOptimization",
    "SimulationHistoryEntry",
    "ToolCatalogEntry",
    "ToolExecutionRecord",
    "UserGoal",
]
