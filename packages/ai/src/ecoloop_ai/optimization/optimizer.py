"""Public entry point for the optimization engine foundation."""

from __future__ import annotations

from ecoloop_ai.optimization.config import OptimizationConfig
from ecoloop_ai.optimization.goal_interpreter import GoalInterpreter
from ecoloop_ai.optimization.models import (
    DecisionInput,
    DecisionSummary,
    GoalInterpretation,
    OptimizationRequest,
    OptimizationSession,
)
from ecoloop_ai.optimization.planner import OptimizationPlanner
from ecoloop_ai.optimization.workflow import OptimizationWorkflow


class OptimizationEngine:
    """Prepare sessions and expose pre-simulation reasoning through one public API."""

    def __init__(
        self,
        *,
        config: OptimizationConfig | None = None,
        workflow: OptimizationWorkflow | None = None,
        goal_interpreter: GoalInterpreter | None = None,
        planner: OptimizationPlanner | None = None,
    ) -> None:
        """Initialize the engine with dependency-injected configuration and services."""
        resolved_config = config or OptimizationConfig()
        self._config = resolved_config
        self._workflow = workflow or OptimizationWorkflow(resolved_config)
        self._goal_interpreter = goal_interpreter or GoalInterpreter(resolved_config)
        self._planner = planner or OptimizationPlanner(config=resolved_config)

    @property
    def config(self) -> OptimizationConfig:
        """Expose the immutable optimization configuration."""
        return self._config

    def prepare(self, request: OptimizationRequest) -> OptimizationSession:
        """Create the initial optimization session for one request."""
        return self._workflow.start(request)

    def interpret_goal(self, goal_text: str) -> GoalInterpretation:
        """Interpret a natural-language optimization goal into structured models."""
        return self._goal_interpreter.interpret(goal_text)

    def reason(
        self,
        decision_input: DecisionInput,
    ) -> DecisionSummary:
        """Create the complete pre-simulation reasoning summary for one decision input."""
        return self._planner.analyze(decision_input)

    def workflow_stages(self) -> tuple[str, ...]:
        """Expose the ordered workflow stage names for observability and tooling."""
        return tuple(stage.value for stage in self._workflow.stages)


__all__ = ["OptimizationEngine"]
