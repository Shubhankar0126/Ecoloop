"""Engineering hypothesis models and generation services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.constraints import ConstraintEvaluation
from ecoloop_ai.optimization.exceptions import HypothesisGenerationError
from ecoloop_ai.optimization.objectives import OptimizationObjectiveKind, objective_priority_weight
from ecoloop_ai.optimization.scoring import CompositeScore

if TYPE_CHECKING:
    from ecoloop_ai.optimization.config import OptimizationConfig
    from ecoloop_ai.optimization.models import DecisionInput, ObjectiveEvaluation


class HypothesisCategory(StrEnum):
    """Supported engineering hypothesis categories."""

    HVAC = "hvac"
    LIGHTING = "lighting"
    ENVELOPE = "envelope"
    VENTILATION = "ventilation"
    SCHEDULES = "schedules"
    OCCUPANCY = "occupancy"
    CONTROLS = "controls"
    EQUIPMENT = "equipment"
    CUSTOM = "custom"


class ImpactDirection(StrEnum):
    """Expected direction of impact for one engineering hypothesis."""

    DECREASE = "decrease"
    INCREASE = "increase"
    STABILIZE = "stabilize"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ImpactMagnitude(StrEnum):
    """Expected magnitude of impact for one engineering hypothesis."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(StrEnum):
    """Normalized risk levels used by the pre-simulation reasoning layer."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactEstimate(BaseModel):
    """A structured expectation for how one hypothesis affects a specific dimension."""

    model_config = ConfigDict(frozen=True)

    direction: ImpactDirection = ImpactDirection.UNKNOWN
    magnitude: ImpactMagnitude = ImpactMagnitude.LOW
    summary: str = Field(min_length=1, default="Impact requires further analysis.")


class EngineeringHypothesis(BaseModel):
    """A reasoned engineering idea that can later drive one simulation candidate."""

    model_config = ConfigDict(frozen=True)

    hypothesis_id: UUID = Field(default_factory=uuid4)
    category: HypothesisCategory = HypothesisCategory.CONTROLS
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    engineering_reason: str | None = None
    expected_energy_impact: ImpactEstimate = Field(default_factory=ImpactEstimate)
    expected_comfort_impact: ImpactEstimate = Field(default_factory=ImpactEstimate)
    expected_cost_impact: ImpactEstimate = Field(default_factory=ImpactEstimate)
    expected_carbon_impact: ImpactEstimate = Field(default_factory=ImpactEstimate)
    expected_improvement_percent: float | None = Field(default=None, ge=0, le=100)
    expected_benefits: tuple[str, ...] = ()
    potential_risks: tuple[str, ...] = ()
    affected_systems: tuple[str, ...] = ()
    confidence: float = Field(default=0.5, ge=0, le=1)
    estimated_risk: RiskLevel = RiskLevel.MEDIUM


class RiskAssessment(BaseModel):
    """Pre-simulation risk assessment for one engineering hypothesis."""

    model_config = ConfigDict(frozen=True)

    hypothesis_id: UUID
    level: RiskLevel
    explanation: str = Field(min_length=1)
    mitigation_suggestions: tuple[str, ...] = ()
    triggering_factors: tuple[str, ...] = ()
    constraint_evaluations: tuple[ConstraintEvaluation, ...] = ()


class HypothesisEvaluation(BaseModel):
    """Structured assessment of one generated engineering hypothesis."""

    model_config = ConfigDict(frozen=True)

    hypothesis: EngineeringHypothesis
    objective_alignment_score: float = Field(ge=0, le=100)
    overall_score: CompositeScore
    risk_assessment: RiskAssessment
    constraint_evaluations: tuple[ConstraintEvaluation, ...] = ()
    accepted: bool
    rationale: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class HypothesisTemplate:
    """Static template used to generate reusable engineering hypotheses."""

    category: HypothesisCategory
    title: str
    summary: str
    engineering_reason: str
    expected_energy_impact: ImpactEstimate
    expected_comfort_impact: ImpactEstimate
    expected_cost_impact: ImpactEstimate
    expected_carbon_impact: ImpactEstimate
    affected_systems: tuple[str, ...]
    confidence: float
    estimated_risk: RiskLevel
    expected_improvement_percent: float | None = None
    expected_benefits: tuple[str, ...] = ()
    potential_risks: tuple[str, ...] = ()


class HypothesisEngine:
    """Generate reusable engineering hypotheses for structured optimization goals."""

    _catalog: ClassVar[dict[OptimizationObjectiveKind, tuple[HypothesisTemplate, ...]]] = {
        OptimizationObjectiveKind.TOTAL_SITE_ENERGY: (
            HypothesisTemplate(
                category=HypothesisCategory.SCHEDULES,
                title="Adjust operating hours",
                summary="Trim non-critical operating hours to remove avoidable site energy use.",
                engineering_reason=(
                    "Schedule tightening is often the lowest-risk first step for whole-building "
                    "energy reduction."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Less off-hour equipment runtime should reduce site energy.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.STABILIZE,
                    magnitude=ImpactMagnitude.LOW,
                    summary="Comfort should remain stable if occupied schedules are preserved.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower runtime usually lowers utility cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Reduced energy use usually reduces emissions.",
                ),
                affected_systems=("Schedules", "HVAC", "Lighting"),
                confidence=0.66,
                estimated_risk=RiskLevel.LOW,
                expected_benefits=("Reduce off-hour energy waste.",),
                potential_risks=("Occupancy assumptions may be inaccurate.",),
            ),
        ),
        OptimizationObjectiveKind.HVAC_ENERGY: (
            HypothesisTemplate(
                category=HypothesisCategory.HVAC,
                title="Reduce HVAC runtime",
                summary=(
                    "Shorten unnecessary HVAC runtime in unoccupied or lightly occupied periods."
                ),
                engineering_reason=(
                    "HVAC runtime is a primary driver of energy use and often "
                    "contains scheduling slack."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Runtime reduction can materially lower HVAC energy.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Poorly chosen runtime trims could reduce comfort margin.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Lower runtime should reduce utility cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Lower HVAC energy should reduce carbon emissions.",
                ),
                affected_systems=("Air handling", "Schedules"),
                confidence=0.72,
                estimated_risk=RiskLevel.MEDIUM,
                expected_benefits=("Reduce fan and conditioning runtime.",),
                potential_risks=("Occupied comfort drift if schedules are too aggressive.",),
            ),
            HypothesisTemplate(
                category=HypothesisCategory.CONTROLS,
                title="Optimize equipment sequencing",
                summary="Improve staging and sequencing to reduce simultaneous HVAC operation.",
                engineering_reason=(
                    "Better sequencing can eliminate avoidable overlap between HVAC subsystems."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Improved sequencing typically trims avoidable HVAC load.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.STABILIZE,
                    magnitude=ImpactMagnitude.LOW,
                    summary="Comfort should remain stable if sequencing remains coordinated.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower overlap should reduce cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower HVAC load should reduce emissions.",
                ),
                affected_systems=("Plant sequencing", "Controls"),
                confidence=0.68,
                estimated_risk=RiskLevel.MEDIUM,
            ),
        ),
        OptimizationObjectiveKind.COOLING_ENERGY: (
            HypothesisTemplate(
                category=HypothesisCategory.HVAC,
                title="Increase cooling setpoint",
                summary=(
                    "Raise the occupied cooling setpoint within comfort limits "
                    "to reduce cooling load."
                ),
                engineering_reason=(
                    "Higher cooling setpoints directly reduce sensible cooling "
                    "demand in many buildings."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Cooling energy should decrease if setpoints remain acceptable.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Some warm-sensitive zones may lose comfort margin.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Lower cooling demand should reduce cooling cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="Lower cooling electricity should reduce emissions.",
                ),
                affected_systems=("Zone setpoints", "Cooling plant"),
                confidence=0.74,
                estimated_risk=RiskLevel.MEDIUM,
                expected_improvement_percent=8.0,
            ),
        ),
        OptimizationObjectiveKind.HEATING_ENERGY: (
            HypothesisTemplate(
                category=HypothesisCategory.HVAC,
                title="Reduce heating setpoint",
                summary="Lower the occupied heating setpoint within acceptable comfort bounds.",
                engineering_reason=(
                    "Slightly lower heating setpoints reduce space heating "
                    "demand across the building."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Heating demand should decrease when setpoints are reduced.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Perimeter or cold-sensitive spaces may lose comfort margin.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower heating load should reduce cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower heating demand should reduce emissions.",
                ),
                affected_systems=("Zone setpoints", "Heating plant"),
                confidence=0.7,
                estimated_risk=RiskLevel.MEDIUM,
            ),
        ),
        OptimizationObjectiveKind.THERMAL_COMFORT: (
            HypothesisTemplate(
                category=HypothesisCategory.CONTROLS,
                title="Tighten occupied control bands",
                summary=(
                    "Reduce control drift during occupied periods to stabilize comfort outcomes."
                ),
                engineering_reason=(
                    "Tighter occupied control logic often improves comfort "
                    "consistency across zones."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.INCREASE,
                    magnitude=ImpactMagnitude.LOW,
                    summary="Improved comfort may slightly increase conditioning energy.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.INCREASE,
                    magnitude=ImpactMagnitude.HIGH,
                    summary="More stable control bands should improve comfort delivery.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.INCREASE,
                    magnitude=ImpactMagnitude.LOW,
                    summary="Comfort-first tuning may slightly increase cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.INCREASE,
                    magnitude=ImpactMagnitude.LOW,
                    summary="More conditioning may modestly increase emissions.",
                ),
                affected_systems=("Zone controls", "BAS logic"),
                confidence=0.69,
                estimated_risk=RiskLevel.MEDIUM,
            ),
        ),
        OptimizationObjectiveKind.LIGHTING_ENERGY: (
            HypothesisTemplate(
                category=HypothesisCategory.LIGHTING,
                title="Reduce lighting schedule",
                summary="Trim lighting schedules outside verified occupied hours.",
                engineering_reason=(
                    "Lighting schedules are often more conservative than actual occupancy needs."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Shorter lighting schedules should reduce lighting energy.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.MIXED,
                    magnitude=ImpactMagnitude.LOW,
                    summary="Lighting changes may affect perceived comfort or task visibility.",
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower runtime should reduce cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower electric lighting use should reduce emissions.",
                ),
                affected_systems=("Lighting controls", "Schedules"),
                confidence=0.71,
                estimated_risk=RiskLevel.LOW,
            ),
        ),
        OptimizationObjectiveKind.VENTILATION_EFFICIENCY: (
            HypothesisTemplate(
                category=HypothesisCategory.VENTILATION,
                title="Optimize ventilation schedule",
                summary=(
                    "Align outdoor-air delivery more closely to occupancy and "
                    "actual ventilation need."
                ),
                engineering_reason=(
                    "Ventilation often presents schedule and control opportunities "
                    "without major hardware changes."
                ),
                expected_energy_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Better ventilation timing can reduce conditioning load.",
                ),
                expected_comfort_impact=ImpactEstimate(
                    direction=ImpactDirection.STABILIZE,
                    magnitude=ImpactMagnitude.LOW,
                    summary=(
                        "Comfort should remain stable if occupancy requirements are maintained."
                    ),
                ),
                expected_cost_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower outdoor-air conditioning should reduce cost.",
                ),
                expected_carbon_impact=ImpactEstimate(
                    direction=ImpactDirection.DECREASE,
                    magnitude=ImpactMagnitude.MEDIUM,
                    summary="Lower ventilation load should reduce emissions.",
                ),
                affected_systems=("Outdoor air control", "Schedules"),
                confidence=0.67,
                estimated_risk=RiskLevel.MEDIUM,
            ),
        ),
    }

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize the hypothesis engine with injected optimization policy."""
        if config is None:
            from ecoloop_ai.optimization.config import OptimizationConfig as ConfigModel

            config = ConfigModel()

        self._config = config

    def generate(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        *,
        focus_categories: tuple[HypothesisCategory, ...] = (),
        limit: int | None = None,
    ) -> tuple[EngineeringHypothesis, ...]:
        """Generate reusable engineering hypotheses for the provided decision input."""
        max_hypotheses = limit or self._config.reasoning.maximum_generated_hypotheses
        hypotheses: list[EngineeringHypothesis] = []
        seen_titles: set[str] = set()
        ranked_evaluations = sorted(
            objective_evaluations,
            key=lambda item: (
                item.objective.weight * objective_priority_weight(item.objective.priority)
            ),
            reverse=True,
        )
        for evaluation in ranked_evaluations:
            for template in self._templates_for(evaluation.objective.kind, focus_categories):
                if template.title in seen_titles:
                    continue

                hypothesis = self._build_hypothesis(template, evaluation, decision_input)
                if hypothesis.confidence < self._config.reasoning.minimum_hypothesis_confidence:
                    continue

                hypotheses.append(hypothesis)
                seen_titles.add(template.title)
                if len(hypotheses) >= max_hypotheses:
                    return tuple(hypotheses)

        if not hypotheses:
            msg = "The hypothesis engine could not generate candidates for the requested goal."
            raise HypothesisGenerationError(msg, context={"goal": decision_input.goal.summary})

        return tuple(hypotheses)

    def _templates_for(
        self,
        kind: OptimizationObjectiveKind,
        focus_categories: tuple[HypothesisCategory, ...],
    ) -> tuple[HypothesisTemplate, ...]:
        """Return the relevant hypothesis templates for one objective kind."""
        templates = self._catalog.get(
            kind, self._catalog.get(OptimizationObjectiveKind.TOTAL_SITE_ENERGY, ())
        )
        if not focus_categories:
            return templates

        filtered = tuple(
            template for template in templates if template.category in focus_categories
        )
        return filtered or templates

    def _build_hypothesis(
        self,
        template: HypothesisTemplate,
        evaluation: ObjectiveEvaluation,
        decision_input: DecisionInput,
    ) -> EngineeringHypothesis:
        """Materialize one engineering hypothesis from a reusable template."""
        building_name = decision_input.building_metadata.building_name or "the building"
        expected_improvement = template.expected_improvement_percent
        if expected_improvement is None:
            expected_improvement = evaluation.objective.target_reduction_percent

        confidence = min(
            1.0,
            round(template.confidence * max(evaluation.confidence, 0.5), 2),
        )
        return EngineeringHypothesis(
            category=template.category,
            title=template.title,
            summary=f"{template.summary} The current focus is {building_name}.",
            engineering_reason=(
                f"{template.engineering_reason} The current objective score is "
                f"{evaluation.score.value:.1f}/100."
            ),
            expected_energy_impact=template.expected_energy_impact,
            expected_comfort_impact=template.expected_comfort_impact,
            expected_cost_impact=template.expected_cost_impact,
            expected_carbon_impact=template.expected_carbon_impact,
            expected_improvement_percent=expected_improvement,
            expected_benefits=template.expected_benefits,
            potential_risks=template.potential_risks,
            affected_systems=template.affected_systems,
            confidence=confidence,
            estimated_risk=template.estimated_risk,
        )


__all__ = [
    "EngineeringHypothesis",
    "HypothesisCategory",
    "HypothesisEngine",
    "HypothesisEvaluation",
    "ImpactDirection",
    "ImpactEstimate",
    "ImpactMagnitude",
    "RiskAssessment",
    "RiskLevel",
]
