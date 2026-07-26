"""Objective contracts, definitions, and evaluators for optimization reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.metrics import resolve_metric_value
from ecoloop_ai.optimization.scoring import (
    CarbonScore,
    ComfortScore,
    CompositeScore,
    CostScore,
    EnergyScore,
    NormalizedScore,
    PeakDemandScore,
    clamp_score,
    generic_score,
    weighted_average,
)

if TYPE_CHECKING:
    from ecoloop_ai.optimization.models import DecisionInput, ObjectiveEvaluation


class OptimizationDirection(StrEnum):
    """Supported optimization directions for one metric."""

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    BALANCE = "balance"


class ObjectivePriority(StrEnum):
    """Priority levels used to weight optimization objectives."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationObjectiveKind(StrEnum):
    """The supported high-level optimization objective categories."""

    TOTAL_SITE_ENERGY = "total_site_energy"
    HVAC_ENERGY = "hvac_energy"
    COOLING_ENERGY = "cooling_energy"
    HEATING_ENERGY = "heating_energy"
    OPERATING_COST = "operating_cost"
    CARBON_EMISSIONS = "carbon_emissions"
    THERMAL_COMFORT = "thermal_comfort"
    OCCUPANT_SATISFACTION = "occupant_satisfaction"
    PEAK_DEMAND = "peak_demand"
    LIGHTING_ENERGY = "lighting_energy"
    VENTILATION_EFFICIENCY = "ventilation_efficiency"
    COMFORT_AND_ENERGY = "comfort_and_energy"
    EMISSIONS_AND_COST = "emissions_and_cost"
    CUSTOM = "custom"


class OptimizationObjective(BaseModel):
    """One measurable objective that participates in the optimization goal."""

    model_config = ConfigDict(frozen=True)

    kind: OptimizationObjectiveKind
    metric_name: str = Field(min_length=1)
    direction: OptimizationDirection = OptimizationDirection.MINIMIZE
    weight: float = Field(default=1.0, gt=0, le=100)
    priority: ObjectivePriority = ObjectivePriority.MEDIUM
    target_value: float | None = None
    target_reduction_percent: float | None = Field(default=None, gt=0, le=100)
    tolerance: float = Field(default=0.05, ge=0)
    unit: str | None = None
    rationale: str | None = None


class OptimizationGoal(BaseModel):
    """The complete goal definition for one optimization session."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    objectives: tuple[OptimizationObjective, ...] = Field(min_length=1)
    success_criteria: tuple[str, ...] = ()
    business_constraints: tuple[str, ...] = ()
    source_text: str | None = None


@dataclass(frozen=True, slots=True)
class ObjectiveMetadata:
    """Static metadata that configures one concrete objective evaluator."""

    display_name: str
    description: str
    default_metric_name: str
    default_direction: OptimizationDirection
    score_type: type[NormalizedScore]


_OBJECTIVE_METADATA: dict[OptimizationObjectiveKind, ObjectiveMetadata] = {
    OptimizationObjectiveKind.TOTAL_SITE_ENERGY: ObjectiveMetadata(
        display_name="Energy",
        description="Reduce total building energy consumption.",
        default_metric_name="total_site_energy_kwh",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=EnergyScore,
    ),
    OptimizationObjectiveKind.HVAC_ENERGY: ObjectiveMetadata(
        display_name="HVAC Energy",
        description="Reduce HVAC system energy use while preserving operations.",
        default_metric_name="hvac_energy_kwh",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=EnergyScore,
    ),
    OptimizationObjectiveKind.COOLING_ENERGY: ObjectiveMetadata(
        display_name="Cooling Energy",
        description="Reduce cooling energy demand and related HVAC load.",
        default_metric_name="cooling_energy_kwh",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=EnergyScore,
    ),
    OptimizationObjectiveKind.HEATING_ENERGY: ObjectiveMetadata(
        display_name="Heating Energy",
        description="Reduce heating energy demand without destabilizing comfort.",
        default_metric_name="heating_energy_kwh",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=EnergyScore,
    ),
    OptimizationObjectiveKind.THERMAL_COMFORT: ObjectiveMetadata(
        display_name="Comfort",
        description="Improve occupant thermal comfort conditions.",
        default_metric_name="average_ppd_percent",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=ComfortScore,
    ),
    OptimizationObjectiveKind.CARBON_EMISSIONS: ObjectiveMetadata(
        display_name="Carbon",
        description="Reduce operational carbon emissions.",
        default_metric_name="carbon_emissions_kgco2e",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=CarbonScore,
    ),
    OptimizationObjectiveKind.OPERATING_COST: ObjectiveMetadata(
        display_name="Cost",
        description="Reduce operating cost while maintaining acceptable performance.",
        default_metric_name="operating_cost_usd",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=CostScore,
    ),
    OptimizationObjectiveKind.PEAK_DEMAND: ObjectiveMetadata(
        display_name="Peak Demand",
        description="Reduce electrical peak demand exposure.",
        default_metric_name="peak_demand_kw",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=PeakDemandScore,
    ),
    OptimizationObjectiveKind.LIGHTING_ENERGY: ObjectiveMetadata(
        display_name="Lighting Energy",
        description="Reduce lighting energy without compromising usage requirements.",
        default_metric_name="lighting_energy_kwh",
        default_direction=OptimizationDirection.MINIMIZE,
        score_type=EnergyScore,
    ),
    OptimizationObjectiveKind.VENTILATION_EFFICIENCY: ObjectiveMetadata(
        display_name="Ventilation Efficiency",
        description="Improve ventilation effectiveness and outside-air efficiency.",
        default_metric_name="ventilation_efficiency_percent",
        default_direction=OptimizationDirection.MAXIMIZE,
        score_type=ComfortScore,
    ),
    OptimizationObjectiveKind.CUSTOM: ObjectiveMetadata(
        display_name="Custom Objective",
        description="Evaluate a custom optimization signal.",
        default_metric_name="custom_goal_score",
        default_direction=OptimizationDirection.BALANCE,
        score_type=NormalizedScore,
    ),
}


def default_metric_name(kind: OptimizationObjectiveKind) -> str:
    """Return the canonical metric name associated with one objective kind."""
    metadata = _OBJECTIVE_METADATA.get(kind, _OBJECTIVE_METADATA[OptimizationObjectiveKind.CUSTOM])
    return metadata.default_metric_name


def default_direction(kind: OptimizationObjectiveKind) -> OptimizationDirection:
    """Return the default direction associated with one objective kind."""
    metadata = _OBJECTIVE_METADATA.get(kind, _OBJECTIVE_METADATA[OptimizationObjectiveKind.CUSTOM])
    return metadata.default_direction


def objective_priority_weight(priority: ObjectivePriority) -> float:
    """Convert a semantic priority into a stable numeric weight."""
    return {
        ObjectivePriority.LOW: 0.75,
        ObjectivePriority.MEDIUM: 1.0,
        ObjectivePriority.HIGH: 1.25,
        ObjectivePriority.CRITICAL: 1.5,
    }[priority]


class ObjectiveContract(Protocol):
    """Framework-independent contract shared by all optimization objectives."""

    definition: OptimizationObjective

    def name(self) -> str:
        """Return the objective display name."""

    def description(self) -> str:
        """Return the objective description."""

    def priority(self) -> ObjectivePriority:
        """Return the objective priority."""

    def required_metrics(self) -> tuple[str, ...]:
        """Return the metric names needed to evaluate the objective."""

    def score(self, decision_input: DecisionInput) -> NormalizedScore:
        """Compute the normalized score for the current state."""

    def improvement(self, decision_input: DecisionInput) -> float | None:
        """Return the amount of improvement still required to satisfy the objective."""

    def is_satisfied(self, decision_input: DecisionInput) -> bool:
        """Return whether the objective is currently satisfied."""

    def confidence(self, decision_input: DecisionInput) -> float:
        """Return confidence in the objective assessment."""

    def evaluate(self, decision_input: DecisionInput) -> ObjectiveEvaluation:
        """Create a structured objective evaluation record."""


class BaseObjective:
    """Shared objective logic for metric-oriented optimization goals."""

    _metadata: ObjectiveMetadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.CUSTOM]

    def __init__(self, definition: OptimizationObjective) -> None:
        self.definition = definition

    def name(self) -> str:
        """Return the objective display name."""
        return self._metadata.display_name

    def description(self) -> str:
        """Return the objective description."""
        if self.definition.rationale:
            return f"{self._metadata.description} {self.definition.rationale}"

        return self._metadata.description

    def priority(self) -> ObjectivePriority:
        """Return the objective priority."""
        return self.definition.priority

    def required_metrics(self) -> tuple[str, ...]:
        """Return the metric names needed to evaluate the objective."""
        return (self.definition.metric_name,)

    def score(self, decision_input: DecisionInput) -> NormalizedScore:
        """Compute the normalized score for the current state."""
        current_value, target_value = self._current_and_target(decision_input)
        if current_value is None:
            return generic_score(
                0.0, f"{self.name()} cannot be scored because the metric is absent."
            )

        if target_value is None:
            return generic_score(
                50.0,
                f"{self.name()} has no explicit target, so the current score is provisional.",
            )

        score_value = self._score_value(
            current_value=current_value,
            target_value=target_value,
            tolerance=self._absolute_tolerance(target_value),
        )
        return self._build_score(score_value, current_value, target_value)

    def improvement(self, decision_input: DecisionInput) -> float | None:
        """Return the amount of improvement still required to satisfy the objective."""
        current_value, target_value = self._current_and_target(decision_input)
        if current_value is None or target_value is None:
            return None

        if self.definition.direction is OptimizationDirection.MINIMIZE:
            return max(current_value - target_value, 0.0)

        if self.definition.direction is OptimizationDirection.MAXIMIZE:
            return max(target_value - current_value, 0.0)

        return abs(current_value - target_value)

    def is_satisfied(self, decision_input: DecisionInput) -> bool:
        """Return whether the objective is currently satisfied."""
        current_value, target_value = self._current_and_target(decision_input)
        if current_value is None or target_value is None:
            return False

        tolerance = self._absolute_tolerance(target_value)
        if self.definition.direction is OptimizationDirection.MINIMIZE:
            return current_value <= target_value + tolerance

        if self.definition.direction is OptimizationDirection.MAXIMIZE:
            return current_value >= target_value - tolerance

        return abs(current_value - target_value) <= tolerance

    def confidence(self, decision_input: DecisionInput) -> float:
        """Return confidence in the objective assessment."""
        value = resolve_metric_value(decision_input.current_metrics, self.definition.metric_name)
        return 1.0 if value is not None else 0.0

    def evaluate(self, decision_input: DecisionInput) -> ObjectiveEvaluation:
        """Create a structured objective evaluation record."""
        from ecoloop_ai.optimization.models import ObjectiveEvaluation

        current_value, target_value = self._current_and_target(decision_input)
        return ObjectiveEvaluation(
            objective=self.definition,
            name=self.name(),
            description=self.description(),
            score=self.score(decision_input),
            current_value=current_value,
            target_value=target_value,
            required_improvement=self.improvement(decision_input),
            satisfied=self.is_satisfied(decision_input),
            confidence=self.confidence(decision_input),
            required_metrics=self.required_metrics(),
            rationale=self._evaluation_rationale(current_value, target_value),
        )

    def _current_and_target(
        self,
        decision_input: DecisionInput,
    ) -> tuple[float | None, float | None]:
        """Resolve the current and target metric values used for scoring."""
        current_value = resolve_metric_value(
            decision_input.current_metrics,
            self.definition.metric_name,
        )
        target_value = self._resolve_target_value(current_value)
        return current_value, target_value

    def _resolve_target_value(self, current_value: float | None) -> float | None:
        """Resolve the concrete target value for one objective."""
        if self.definition.target_value is not None:
            return self.definition.target_value

        if current_value is None or self.definition.target_reduction_percent is None:
            return None

        change_factor = self.definition.target_reduction_percent / 100.0
        if self.definition.direction is OptimizationDirection.MINIMIZE:
            return current_value * max(0.0, 1.0 - change_factor)

        if self.definition.direction is OptimizationDirection.MAXIMIZE:
            return current_value * (1.0 + change_factor)

        return current_value

    def _absolute_tolerance(self, target_value: float) -> float:
        """Convert relative tolerances into an absolute target tolerance."""
        if self.definition.tolerance <= 1.0:
            return abs(target_value) * self.definition.tolerance

        return self.definition.tolerance

    def _score_value(
        self,
        *,
        current_value: float,
        target_value: float,
        tolerance: float,
    ) -> float:
        """Score one objective against the current metrics and target."""
        if self.definition.direction is OptimizationDirection.MINIMIZE:
            if current_value <= target_value + tolerance:
                return 100.0

            scale = max(abs(target_value), 1.0)
            return clamp_score(100.0 - ((current_value - target_value - tolerance) / scale) * 100.0)

        if self.definition.direction is OptimizationDirection.MAXIMIZE:
            if current_value >= target_value - tolerance:
                return 100.0

            scale = max(abs(target_value), 1.0)
            return clamp_score(100.0 - ((target_value - tolerance - current_value) / scale) * 100.0)

        deviation = abs(current_value - target_value)
        scale = max(abs(target_value), 1.0)
        if deviation <= tolerance:
            return 100.0

        return clamp_score(100.0 - ((deviation - tolerance) / scale) * 100.0)

    def _build_score(
        self,
        score_value: float,
        current_value: float,
        target_value: float,
    ) -> NormalizedScore:
        """Instantiate the score model associated with the concrete objective type."""
        summary = (
            f"{self.name()} current value is {current_value:.2f}"
            f" against a target of {target_value:.2f} {self.definition.unit or ''}."
        ).strip()
        score_type = self._metadata.score_type
        if score_type is NormalizedScore:
            return generic_score(score_value, summary)

        typed_score_type = cast(
            type[EnergyScore]
            | type[ComfortScore]
            | type[CarbonScore]
            | type[CostScore]
            | type[PeakDemandScore],
            score_type,
        )
        return typed_score_type(value=score_value, summary=summary)

    def _evaluation_rationale(
        self,
        current_value: float | None,
        target_value: float | None,
    ) -> str:
        """Build a concise explanation for one objective evaluation."""
        unit = self.definition.unit or ""
        if current_value is None:
            return (
                f"{self.name()} could not be evaluated because "
                f"{self.definition.metric_name} is missing."
            )

        if target_value is None:
            return f"{self.name()} uses {current_value:.2f} {unit} as the current baseline."

        direction = self.definition.direction.value
        return (
            f"{self.name()} compares the current value of {current_value:.2f} {unit} "
            f"against a {direction} target of {target_value:.2f} {unit}."
        ).strip()


class EnergyObjective(BaseObjective):
    """Objective evaluator for total site energy reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.TOTAL_SITE_ENERGY]


class HVACObjective(BaseObjective):
    """Objective evaluator for HVAC energy reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.HVAC_ENERGY]


class CoolingObjective(BaseObjective):
    """Objective evaluator for cooling energy reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.COOLING_ENERGY]


class HeatingObjective(BaseObjective):
    """Objective evaluator for heating energy reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.HEATING_ENERGY]


class ComfortObjective(BaseObjective):
    """Objective evaluator for thermal comfort improvement."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.THERMAL_COMFORT]


class CarbonObjective(BaseObjective):
    """Objective evaluator for operational carbon reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.CARBON_EMISSIONS]


class CostObjective(BaseObjective):
    """Objective evaluator for operating-cost reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.OPERATING_COST]


class PeakDemandObjective(BaseObjective):
    """Objective evaluator for peak-demand reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.PEAK_DEMAND]


class LightingObjective(BaseObjective):
    """Objective evaluator for lighting-energy reduction."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.LIGHTING_ENERGY]


class VentilationObjective(BaseObjective):
    """Objective evaluator for ventilation efficiency improvement."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.VENTILATION_EFFICIENCY]


class CustomObjective(BaseObjective):
    """Fallback evaluator used for custom or otherwise unmapped objectives."""

    _metadata = _OBJECTIVE_METADATA[OptimizationObjectiveKind.CUSTOM]


class CompositeObjective:
    """Weighted aggregate objective for multi-objective optimization goals."""

    def __init__(self, goal: OptimizationGoal, objectives: tuple[ObjectiveContract, ...]) -> None:
        self.definition = OptimizationObjective(
            kind=OptimizationObjectiveKind.CUSTOM,
            metric_name="composite_score",
            direction=OptimizationDirection.MAXIMIZE,
            weight=sum(item.definition.weight for item in objectives) or 1.0,
            priority=ObjectivePriority.HIGH,
            target_value=100.0,
            unit="score",
            rationale=goal.summary,
        )
        self._goal = goal
        self._objectives = objectives

    def name(self) -> str:
        """Return the objective display name."""
        return "Composite Objective"

    def description(self) -> str:
        """Return the objective description."""
        return "Weighted aggregate across all structured optimization objectives."

    def priority(self) -> ObjectivePriority:
        """Return the objective priority."""
        return ObjectivePriority.HIGH

    def required_metrics(self) -> tuple[str, ...]:
        """Return the metric names needed to evaluate the composite objective."""
        metric_names = {
            metric_name
            for objective in self._objectives
            for metric_name in objective.required_metrics()
        }
        return tuple(sorted(metric_names))

    def score(self, decision_input: DecisionInput) -> CompositeScore:
        """Compute the weighted aggregate score across all objective components."""
        component_scores = tuple(objective.score(decision_input) for objective in self._objectives)
        weighted_score = weighted_average(
            tuple(
                (
                    objective.score(decision_input),
                    objective.definition.weight * objective_priority_weight(objective.priority()),
                )
                for objective in self._objectives
            )
        )
        return CompositeScore(
            value=weighted_score,
            summary="Composite score across all evaluated optimization objectives.",
            component_scores=component_scores,
        )

    def improvement(self, decision_input: DecisionInput) -> float | None:
        """Return the weighted average remaining improvement across components."""
        improvement_pairs = tuple(
            (
                objective.improvement(decision_input),
                objective.definition.weight * objective_priority_weight(objective.priority()),
            )
            for objective in self._objectives
        )
        valid_pairs = tuple(
            (improvement, weight)
            for improvement, weight in improvement_pairs
            if improvement is not None
        )
        if not valid_pairs:
            return None

        total_weight = sum(weight for _, weight in valid_pairs)
        weighted_sum = sum(improvement * weight for improvement, weight in valid_pairs)
        return round(weighted_sum / total_weight, 2)

    def is_satisfied(self, decision_input: DecisionInput) -> bool:
        """Return whether every component objective is currently satisfied."""
        return all(objective.is_satisfied(decision_input) for objective in self._objectives)

    def confidence(self, decision_input: DecisionInput) -> float:
        """Return the average confidence across component objectives."""
        if not self._objectives:
            return 0.0

        total = sum(objective.confidence(decision_input) for objective in self._objectives)
        return round(total / len(self._objectives), 2)

    def evaluate(self, decision_input: DecisionInput) -> ObjectiveEvaluation:
        """Create a structured composite objective evaluation record."""
        from ecoloop_ai.optimization.models import ObjectiveEvaluation

        return ObjectiveEvaluation(
            objective=self.definition,
            name=self.name(),
            description=self.description(),
            score=self.score(decision_input),
            current_value=None,
            target_value=100.0,
            required_improvement=self.improvement(decision_input),
            satisfied=self.is_satisfied(decision_input),
            confidence=self.confidence(decision_input),
            required_metrics=self.required_metrics(),
            rationale=f"{self._goal.summary} is evaluated as a weighted multi-objective score.",
        )


class ObjectiveRegistry:
    """Resolve structured objective definitions into concrete evaluators."""

    _objective_types: ClassVar[dict[OptimizationObjectiveKind, type[BaseObjective]]] = {
        OptimizationObjectiveKind.TOTAL_SITE_ENERGY: EnergyObjective,
        OptimizationObjectiveKind.HVAC_ENERGY: HVACObjective,
        OptimizationObjectiveKind.COOLING_ENERGY: CoolingObjective,
        OptimizationObjectiveKind.HEATING_ENERGY: HeatingObjective,
        OptimizationObjectiveKind.THERMAL_COMFORT: ComfortObjective,
        OptimizationObjectiveKind.CARBON_EMISSIONS: CarbonObjective,
        OptimizationObjectiveKind.OPERATING_COST: CostObjective,
        OptimizationObjectiveKind.PEAK_DEMAND: PeakDemandObjective,
        OptimizationObjectiveKind.LIGHTING_ENERGY: LightingObjective,
        OptimizationObjectiveKind.VENTILATION_EFFICIENCY: VentilationObjective,
        OptimizationObjectiveKind.OCCUPANT_SATISFACTION: ComfortObjective,
    }

    def build_objective(self, definition: OptimizationObjective) -> ObjectiveContract:
        """Build the concrete objective evaluator for one structured definition."""
        objective_type = self._objective_types.get(definition.kind, CustomObjective)
        return objective_type(definition)

    def build(self, goal: OptimizationGoal) -> tuple[ObjectiveContract, ...]:
        """Resolve all structured goal objectives into concrete evaluators."""
        return tuple(self.build_objective(definition) for definition in goal.objectives)

    def composite(self, goal: OptimizationGoal) -> CompositeObjective:
        """Build the composite aggregate objective for one optimization goal."""
        return CompositeObjective(goal, self.build(goal))

    def evaluate(
        self,
        decision_input: DecisionInput,
    ) -> tuple[tuple[ObjectiveEvaluation, ...], CompositeScore]:
        """Evaluate all goal objectives and their weighted aggregate score."""
        objectives = self.build(decision_input.goal)
        evaluations = tuple(objective.evaluate(decision_input) for objective in objectives)
        composite_score = CompositeObjective(decision_input.goal, objectives).score(decision_input)
        return evaluations, composite_score


__all__ = [
    "BaseObjective",
    "CarbonObjective",
    "ComfortObjective",
    "CompositeObjective",
    "CoolingObjective",
    "CostObjective",
    "CustomObjective",
    "EnergyObjective",
    "HVACObjective",
    "HeatingObjective",
    "ObjectiveContract",
    "ObjectivePriority",
    "ObjectiveRegistry",
    "OptimizationDirection",
    "OptimizationGoal",
    "OptimizationObjective",
    "OptimizationObjectiveKind",
    "PeakDemandObjective",
    "VentilationObjective",
    "default_direction",
    "default_metric_name",
    "objective_priority_weight",
]
