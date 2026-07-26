"""Configuration models for the optimization engine foundation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.strategies import OptimizationStrategyKind


class OptimizationIterationSettings(BaseModel):
    """Execution limits that keep optimization loops bounded."""

    model_config = ConfigDict(frozen=True)

    max_iterations: int = Field(default=10, ge=1, le=100)
    max_candidates_per_iteration: int = Field(default=1, ge=1, le=20)


class OptimizationConvergenceSettings(BaseModel):
    """Thresholds used to decide when additional iterations are no longer useful."""

    model_config = ConfigDict(frozen=True)

    threshold: float = Field(default=0.5, ge=0)
    patience: int = Field(default=2, ge=1, le=50)


class OptimizationObservabilitySettings(BaseModel):
    """Controls for retaining explainability and audit artifacts."""

    model_config = ConfigDict(frozen=True)

    explainability: bool = True
    decision_trace: bool = True
    save_history: bool = True


class OptimizationSafetySettings(BaseModel):
    """Safety-oriented feature flags for future optimization execution."""

    model_config = ConfigDict(frozen=True)

    rollback_enabled: bool = True
    risk_analysis: bool = True


class OptimizationReasoningSettings(BaseModel):
    """Tunable defaults for goal interpretation and pre-simulation reasoning."""

    model_config = ConfigDict(frozen=True)

    default_target_reduction_percent: float = Field(default=10.0, gt=0, le=100)
    default_objective_tolerance: float = Field(default=0.05, ge=0, le=1)
    maximum_generated_hypotheses: int = Field(default=5, ge=1, le=20)
    strategy_selection_limit: int = Field(default=3, ge=1, le=10)
    minimum_hypothesis_confidence: float = Field(default=0.35, ge=0, le=1)
    satisfaction_score_threshold: float = Field(default=80.0, ge=0, le=100)
    random_seed: int = 7


class OptimizationConfig(BaseModel):
    """Top-level configuration contract for the optimization engine."""

    model_config = ConfigDict(frozen=True)

    strategy: OptimizationStrategyKind = OptimizationStrategyKind.AI_GUIDED
    iteration: OptimizationIterationSettings = Field(default_factory=OptimizationIterationSettings)
    convergence: OptimizationConvergenceSettings = Field(
        default_factory=OptimizationConvergenceSettings
    )
    observability: OptimizationObservabilitySettings = Field(
        default_factory=OptimizationObservabilitySettings
    )
    safety: OptimizationSafetySettings = Field(default_factory=OptimizationSafetySettings)
    reasoning: OptimizationReasoningSettings = Field(default_factory=OptimizationReasoningSettings)

    def resolve_max_iterations(self, requested_max_iterations: int | None) -> int:
        """Resolve the maximum iteration count for one optimization request."""
        return requested_max_iterations or self.iteration.max_iterations


__all__ = [
    "OptimizationConfig",
    "OptimizationConvergenceSettings",
    "OptimizationIterationSettings",
    "OptimizationObservabilitySettings",
    "OptimizationReasoningSettings",
    "OptimizationSafetySettings",
]
