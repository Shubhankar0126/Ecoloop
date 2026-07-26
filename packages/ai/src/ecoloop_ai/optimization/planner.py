"""Planning models and orchestration for pre-simulation optimization reasoning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.config import OptimizationConfig
from ecoloop_ai.optimization.constraints import (
    ConstraintEvaluation,
    ConstraintEvaluator,
    ConstraintSeverity,
    ConstraintStatus,
)
from ecoloop_ai.optimization.hypothesis import (
    EngineeringHypothesis,
    HypothesisEngine,
    HypothesisEvaluation,
    RiskAssessment,
)
from ecoloop_ai.optimization.objectives import (
    ObjectivePriority,
    ObjectiveRegistry,
    objective_priority_weight,
)
from ecoloop_ai.optimization.risk import RiskAssessor
from ecoloop_ai.optimization.scoring import CompositeScore, generic_score, weighted_average
from ecoloop_ai.optimization.strategies import OptimizationStrategyKind, StrategyRegistry

if TYPE_CHECKING:
    from ecoloop_ai.optimization.models import (
        DecisionInput,
        DecisionSummary,
        ObjectiveEvaluation,
        StrategyDecision,
    )


class OptimizationPlanStep(BaseModel):
    """One planned step in a future optimization iteration."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    success_signal: str = Field(min_length=1)


class OptimizationPlan(BaseModel):
    """A reusable structured plan that can guide a future optimization loop."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    strategy_kind: OptimizationStrategyKind
    steps: tuple[OptimizationPlanStep, ...] = Field(min_length=1)


class OptimizationPlanner:
    """Orchestrate objective evaluation, hypothesis generation, and strategy choice."""

    def __init__(
        self,
        *,
        config: OptimizationConfig | None = None,
        objective_registry: ObjectiveRegistry | None = None,
        hypothesis_engine: HypothesisEngine | None = None,
        constraint_evaluator: ConstraintEvaluator | None = None,
        risk_assessor: RiskAssessor | None = None,
        strategy_registry: StrategyRegistry | None = None,
    ) -> None:
        self._config = config or OptimizationConfig()
        self._objective_registry = objective_registry or ObjectiveRegistry()
        self._hypothesis_engine = hypothesis_engine or HypothesisEngine(self._config)
        self._constraint_evaluator = constraint_evaluator or ConstraintEvaluator()
        self._risk_assessor = risk_assessor or RiskAssessor(self._config)
        self._strategy_registry = strategy_registry or StrategyRegistry(config=self._config)

    def analyze(
        self,
        decision_input: DecisionInput,
        *,
        strategy_kind: OptimizationStrategyKind | None = None,
    ) -> DecisionSummary:
        """Build the complete pre-simulation reasoning summary for one decision input."""
        from ecoloop_ai.optimization.models import DecisionSummary

        objective_evaluations, composite_score = self._objective_registry.evaluate(decision_input)
        current_constraint_evaluations = self._constraint_evaluator.evaluate_current(decision_input)
        resolved_strategy = self._strategy_registry.resolve(
            strategy_kind or decision_input.preferred_strategy or self._config.strategy
        )
        generated_hypotheses = self._hypothesis_engine.generate(
            decision_input,
            objective_evaluations,
            focus_categories=resolved_strategy.hypothesis_categories(objective_evaluations),
            limit=resolved_strategy.generation_limit(),
        )
        hypothesis_evaluations = tuple(
            self._evaluate_hypothesis(
                decision_input,
                objective_evaluations,
                current_constraint_evaluations,
                hypothesis,
            )
            for hypothesis in generated_hypotheses
        )
        strategy_decision = resolved_strategy.decide(
            decision_input,
            objective_evaluations,
            hypothesis_evaluations,
        )
        return DecisionSummary(
            goal=decision_input.goal,
            objective_evaluations=objective_evaluations,
            composite_score=composite_score,
            constraint_evaluations=current_constraint_evaluations,
            hypothesis_evaluations=hypothesis_evaluations,
            strategy_decision=strategy_decision,
            summary=self._summary(decision_input, strategy_decision, objective_evaluations),
            next_focus_areas=tuple(
                item.hypothesis.title
                for item in hypothesis_evaluations
                if item.hypothesis.hypothesis_id in strategy_decision.selected_hypothesis_ids
            ),
        )

    def _evaluate_hypothesis(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        current_constraint_evaluations: tuple[ConstraintEvaluation, ...],
        hypothesis: EngineeringHypothesis,
    ) -> HypothesisEvaluation:
        """Evaluate one generated engineering hypothesis against objectives and constraints."""
        constraint_evaluations = self._constraint_evaluator.evaluate_hypothesis(
            decision_input,
            hypothesis,
        )
        risk_assessment = self._risk_assessor.assess(
            hypothesis,
            constraint_evaluations=constraint_evaluations,
        )
        alignment_score = self._objective_alignment_score(hypothesis, objective_evaluations)
        alignment_component = generic_score(
            alignment_score,
            "Objective-alignment score for the generated engineering hypothesis.",
        )
        viability_component = generic_score(
            self._viability_score(risk_assessment, constraint_evaluations),
            "Risk-adjusted viability score for the generated engineering hypothesis.",
        )
        overall_score = CompositeScore(
            value=weighted_average(((alignment_component, 0.7), (viability_component, 0.3))),
            summary="Composite hypothesis score combining alignment and viability.",
            component_scores=(alignment_component, viability_component),
        )
        accepted = self._is_hypothesis_accepted(risk_assessment, constraint_evaluations)
        del current_constraint_evaluations
        return HypothesisEvaluation(
            hypothesis=hypothesis,
            objective_alignment_score=alignment_score,
            overall_score=overall_score,
            risk_assessment=risk_assessment,
            constraint_evaluations=constraint_evaluations,
            accepted=accepted,
            rationale=self._hypothesis_rationale(hypothesis, risk_assessment, accepted),
        )

    def _objective_alignment_score(
        self,
        hypothesis: EngineeringHypothesis,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
    ) -> float:
        """Compute a weighted objective-alignment score for one generated hypothesis."""
        score_pairs = tuple(
            (
                generic_score(
                    self._alignment_for_objective(hypothesis, evaluation),
                    f"Alignment score for {evaluation.name}.",
                ),
                evaluation.objective.weight
                * objective_priority_weight(ObjectivePriority(evaluation.objective.priority)),
            )
            for evaluation in objective_evaluations
        )
        return weighted_average(score_pairs)

    def _alignment_for_objective(
        self,
        hypothesis: EngineeringHypothesis,
        evaluation: ObjectiveEvaluation,
    ) -> float:
        """Estimate how well one hypothesis aligns to a single objective."""
        objective_kind = evaluation.objective.kind
        if objective_kind in {
            objective_kind.TOTAL_SITE_ENERGY,
            objective_kind.HVAC_ENERGY,
            objective_kind.COOLING_ENERGY,
            objective_kind.HEATING_ENERGY,
            objective_kind.LIGHTING_ENERGY,
            objective_kind.PEAK_DEMAND,
        }:
            base_score = _impact_alignment_score(hypothesis.expected_energy_impact.direction.value)
        elif objective_kind is objective_kind.THERMAL_COMFORT:
            base_score = _comfort_alignment_score(
                hypothesis.expected_comfort_impact.direction.value
            )
        elif objective_kind is objective_kind.CARBON_EMISSIONS:
            base_score = _impact_alignment_score(hypothesis.expected_carbon_impact.direction.value)
        elif objective_kind is objective_kind.OPERATING_COST:
            base_score = _impact_alignment_score(hypothesis.expected_cost_impact.direction.value)
        else:
            base_score = 60.0

        if hypothesis.category.value in {"hvac", "controls"} and objective_kind in {
            objective_kind.HVAC_ENERGY,
            objective_kind.COOLING_ENERGY,
            objective_kind.HEATING_ENERGY,
        }:
            base_score += 5.0

        return min(100.0, round(base_score + hypothesis.confidence * 10.0, 2))

    def _viability_score(
        self,
        risk_assessment: RiskAssessment,
        constraint_evaluations: tuple[ConstraintEvaluation, ...],
    ) -> float:
        """Estimate how viable one hypothesis is before simulation execution."""
        risk_level = risk_assessment.level
        base_score = {
            "low": 90.0,
            "medium": 72.0,
            "high": 48.0,
            "critical": 20.0,
        }[risk_level.value]
        hard_penalty = 0.0
        soft_penalty = 0.0
        for evaluation in constraint_evaluations:
            status = evaluation.status
            severity = evaluation.constraint.severity
            if status in {ConstraintStatus.VIOLATED, ConstraintStatus.AT_RISK}:
                if severity is ConstraintSeverity.HARD:
                    hard_penalty += 25.0
                else:
                    soft_penalty += 10.0

        return max(0.0, round(base_score - hard_penalty - soft_penalty, 2))

    def _is_hypothesis_accepted(
        self,
        risk_assessment: RiskAssessment,
        constraint_evaluations: tuple[ConstraintEvaluation, ...],
    ) -> bool:
        """Return whether a hypothesis is safe enough to carry forward."""
        if risk_assessment.level.value == "critical":
            return False

        return not any(
            evaluation.status in {ConstraintStatus.VIOLATED, ConstraintStatus.AT_RISK}
            and evaluation.constraint.severity is ConstraintSeverity.HARD
            for evaluation in constraint_evaluations
        )

    @staticmethod
    def _hypothesis_rationale(
        hypothesis: EngineeringHypothesis,
        risk_assessment: RiskAssessment,
        accepted: bool,
    ) -> str:
        """Build a concise rationale for one hypothesis evaluation."""
        state = "accepted" if accepted else "flagged"
        return (
            f"{hypothesis.title} was {state} with {risk_assessment.level.value} risk "
            f"because {risk_assessment.explanation}"
        )

    @staticmethod
    def _summary(
        decision_input: DecisionInput,
        strategy_decision: StrategyDecision,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
    ) -> str:
        """Build the top-level reasoning summary for downstream orchestration."""
        unmet_objectives = [item.name for item in objective_evaluations if not item.satisfied]
        if not unmet_objectives:
            return f"{decision_input.goal.summary} is already satisfied by the current metrics."

        return (
            f"{decision_input.goal.summary} remains open for {', '.join(unmet_objectives)}; "
            f"{strategy_decision.strategy_kind.value} prioritized the next hypothesis set."
        )


def _impact_alignment_score(direction: str) -> float:
    """Return a baseline alignment score for directional energy-style impacts."""
    return {
        "decrease": 88.0,
        "stabilize": 60.0,
        "mixed": 42.0,
        "increase": 24.0,
        "unknown": 30.0,
    }[direction]


def _comfort_alignment_score(direction: str) -> float:
    """Return a baseline alignment score for comfort-direction impacts."""
    return {
        "increase": 90.0,
        "stabilize": 76.0,
        "mixed": 44.0,
        "decrease": 24.0,
        "unknown": 36.0,
    }[direction]


__all__ = ["OptimizationPlan", "OptimizationPlanStep", "OptimizationPlanner"]
