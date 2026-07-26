"""LangGraph state model for the EcoLoop AI planning loop."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.memory import AgentMemory
from ecoloop_ai.models import (
    AgentMessage,
    AgentRequest,
    AnalysisResult,
    ConversationTurn,
    CriticResult,
    OptimizationReport,
    PlannerDecision,
    SimulationHistoryEntry,
    ToolExecutionRecord,
    UserGoal,
)
from ecoloop_energyplus import SimulationResult


class AgentState(BaseModel):
    """Immutable shared state passed through the LangGraph workflow."""

    model_config = ConfigDict(frozen=True)

    conversation: tuple[ConversationTurn, ...] = ()
    goal: UserGoal
    simulation_history: tuple[SimulationHistoryEntry, ...] = ()
    current_plan: PlannerDecision | None = None
    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=3, ge=1)
    latest_simulation_result: SimulationResult | None = None
    latest_tool_execution: ToolExecutionRecord | None = None
    latest_analysis: AnalysisResult | None = None
    latest_critique: CriticResult | None = None
    messages: tuple[AgentMessage, ...] = ()
    goal_achieved: bool = False
    memory: AgentMemory
    final_report: OptimizationReport | None = None

    @classmethod
    def from_request(
        cls,
        request: AgentRequest,
        *,
        memory: AgentMemory,
        default_max_iterations: int,
    ) -> AgentState:
        """Create the initial graph state from a validated public request."""
        return cls(
            conversation=request.conversation,
            goal=request.goal,
            simulation_history=(),
            current_plan=None,
            iteration_count=0,
            max_iterations=request.max_iterations or default_max_iterations,
            latest_simulation_result=None,
            latest_tool_execution=None,
            latest_analysis=None,
            latest_critique=None,
            messages=(),
            goal_achieved=False,
            memory=memory,
            final_report=None,
        )


__all__ = ["AgentState"]
