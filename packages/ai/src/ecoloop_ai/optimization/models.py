"""Composite request, session, decision, and result models for the optimization engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.models import BuildingContext
from ecoloop_ai.optimization.constraints import ConstraintEvaluation, OptimizationConstraint
from ecoloop_ai.optimization.convergence import ConvergenceAssessment
from ecoloop_ai.optimization.decision_trace import DecisionStage, DecisionTraceEntry
from ecoloop_ai.optimization.evaluator import CandidateEvaluation
from ecoloop_ai.optimization.explainability import ExplainabilityRecord
from ecoloop_ai.optimization.history import OptimizationHistoryEntry
from ecoloop_ai.optimization.hypothesis import (
    EngineeringHypothesis,
    HypothesisEvaluation,
)
from ecoloop_ai.optimization.metrics import OptimizationMetricSnapshot
from ecoloop_ai.optimization.objectives import OptimizationGoal, OptimizationObjective
from ecoloop_ai.optimization.planner import OptimizationPlan
from ecoloop_ai.optimization.recommendation import OptimizationRecommendation
from ecoloop_ai.optimization.report import OptimizationOutcomeReport
from ecoloop_ai.optimization.rollback import RollbackPlan
from ecoloop_ai.optimization.scoring import CompositeScore, NormalizedScore
from ecoloop_ai.optimization.strategies import (
    OptimizationAggressiveness,
    OptimizationStrategyKind,
)
from ecoloop_energyplus import SimulationMetrics, SimulationResult


class BuildingMetadata(BaseModel):
    """Reusable building metadata consumed by optimization reasoning services."""

    model_config = ConfigDict(frozen=True)

    building_name: str | None = None
    building_type: str | None = None
    floor_area_m2: float | None = Field(default=None, ge=0)
    primary_hvac_system: str | None = None
    control_notes: tuple[str, ...] = ()


class WeatherMetadata(BaseModel):
    """Reusable weather and climate metadata consumed by optimization reasoning."""

    model_config = ConfigDict(frozen=True)

    climate_zone: str | None = None
    season: str | None = None
    peak_cooling_month: str | None = None
    peak_heating_month: str | None = None
    notes: tuple[str, ...] = ()


class GoalInterpretation(BaseModel):
    """Structured interpretation of one natural-language optimization goal."""

    model_config = ConfigDict(frozen=True)

    source_text: str = Field(min_length=1)
    goal: OptimizationGoal
    constraints: tuple[OptimizationConstraint, ...] = ()
    diagnostics: tuple[str, ...] = ()


class DecisionInput(BaseModel):
    """Typed input contract for the optimization reasoning layer."""

    model_config = ConfigDict(frozen=True)

    current_metrics: SimulationMetrics
    goal: OptimizationGoal
    constraints: tuple[OptimizationConstraint, ...] = ()
    building_metadata: BuildingMetadata = Field(default_factory=BuildingMetadata)
    weather_metadata: WeatherMetadata = Field(default_factory=WeatherMetadata)
    building_context: BuildingContext | None = None
    optimization_history: tuple[OptimizationHistoryEntry, ...] = ()
    preferred_strategy: OptimizationStrategyKind | None = None


class ObjectiveEvaluation(BaseModel):
    """Structured evaluation result for one optimization objective."""

    model_config = ConfigDict(frozen=True)

    objective: OptimizationObjective
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    score: NormalizedScore
    current_value: float | None = None
    target_value: float | None = None
    required_improvement: float | None = None
    satisfied: bool
    confidence: float = Field(ge=0, le=1)
    required_metrics: tuple[str, ...] = ()
    rationale: str = Field(min_length=1)


class StrategyDecision(BaseModel):
    """One strategy decision produced by the optimization reasoning layer."""

    model_config = ConfigDict(frozen=True)

    strategy_kind: OptimizationStrategyKind
    prioritized_hypothesis_ids: tuple[UUID, ...] = ()
    selected_hypothesis_ids: tuple[UUID, ...] = ()
    stop_exploring: bool
    aggressiveness: OptimizationAggressiveness
    rationale: str = Field(min_length=1)
    selection_confidence: float = Field(ge=0, le=1)


class DecisionSummary(BaseModel):
    """Top-level reasoning output consumed by later orchestration layers."""

    model_config = ConfigDict(frozen=True)

    goal: OptimizationGoal
    objective_evaluations: tuple[ObjectiveEvaluation, ...]
    composite_score: CompositeScore
    constraint_evaluations: tuple[ConstraintEvaluation, ...] = ()
    hypothesis_evaluations: tuple[HypothesisEvaluation, ...] = ()
    strategy_decision: StrategyDecision
    summary: str = Field(min_length=1)
    next_focus_areas: tuple[str, ...] = ()


class OptimizationStatus(StrEnum):
    """Lifecycle states for one optimization session."""

    PREPARED = "prepared"
    RUNNING = "running"
    CONVERGED = "converged"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandidateStatus(StrEnum):
    """Lifecycle states for one optimization candidate."""

    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    REJECTED = "rejected"
    RETIRED = "retired"


class OptimizationCandidate(BaseModel):
    """A structured optimization candidate captured independently of execution logic."""

    model_config = ConfigDict(frozen=True)

    candidate_id: UUID = Field(default_factory=uuid4)
    iteration_index: int = Field(ge=1)
    strategy_kind: OptimizationStrategyKind
    hypothesis: EngineeringHypothesis
    status: CandidateStatus = CandidateStatus.PROPOSED
    metrics: tuple[OptimizationMetricSnapshot, ...] = ()
    evaluation: CandidateEvaluation | None = None
    simulation_result: SimulationResult | None = None
    notes: tuple[str, ...] = ()


class OptimizationRequest(BaseModel):
    """Public input contract for preparing one optimization session."""

    model_config = ConfigDict(frozen=True)

    goal: OptimizationGoal
    building_context: BuildingContext
    constraints: tuple[OptimizationConstraint, ...] = ()
    preferred_strategy: OptimizationStrategyKind | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=100)
    metadata: dict[str, str] = Field(default_factory=dict)


class OptimizationSession(BaseModel):
    """Immutable workflow state prepared by the optimization engine."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID = Field(default_factory=uuid4)
    request: OptimizationRequest
    status: OptimizationStatus = OptimizationStatus.PREPARED
    current_stage: DecisionStage = DecisionStage.SESSION_CREATED
    active_strategy: OptimizationStrategyKind
    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(ge=1, le=100)
    current_plan: OptimizationPlan | None = None
    best_candidate: OptimizationCandidate | None = None
    candidates: tuple[OptimizationCandidate, ...] = ()
    recommendations: tuple[OptimizationRecommendation, ...] = ()
    trace: tuple[DecisionTraceEntry, ...] = ()
    history: tuple[OptimizationHistoryEntry, ...] = ()
    latest_convergence: ConvergenceAssessment | None = None
    final_report: OptimizationOutcomeReport | None = None
    rollback_plan: RollbackPlan | None = None
    explainability: ExplainabilityRecord | None = None
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OptimizationResult(BaseModel):
    """Final optimization outcome returned when a session terminates."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    status: OptimizationStatus
    goal: OptimizationGoal
    active_strategy: OptimizationStrategyKind
    best_candidate: OptimizationCandidate | None = None
    recommendations: tuple[OptimizationRecommendation, ...] = ()
    final_report: OptimizationOutcomeReport | None = None
    trace: tuple[DecisionTraceEntry, ...] = ()
    history: tuple[OptimizationHistoryEntry, ...] = ()
    explainability: ExplainabilityRecord | None = None
    rollback_plan: RollbackPlan | None = None

    @classmethod
    def from_session(cls, session: OptimizationSession) -> OptimizationResult:
        """Create a final immutable result from the latest workflow session state."""
        return cls(
            session_id=session.session_id,
            status=session.status,
            goal=session.request.goal,
            active_strategy=session.active_strategy,
            best_candidate=session.best_candidate,
            recommendations=session.recommendations,
            final_report=session.final_report,
            trace=session.trace,
            history=session.history,
            explainability=session.explainability,
            rollback_plan=session.rollback_plan,
        )


__all__ = [
    "BuildingMetadata",
    "CandidateStatus",
    "DecisionInput",
    "DecisionSummary",
    "GoalInterpretation",
    "ObjectiveEvaluation",
    "OptimizationCandidate",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizationSession",
    "OptimizationStatus",
    "StrategyDecision",
    "WeatherMetadata",
]
