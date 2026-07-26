"""Constraint models and evaluators for optimization reasoning."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ecoloop_ai.optimization.metrics import resolve_metric_unit, resolve_metric_value

if TYPE_CHECKING:
    from ecoloop_ai.optimization.hypothesis import EngineeringHypothesis
    from ecoloop_ai.optimization.models import DecisionInput


class ConstraintSeverity(StrEnum):
    """The strength of a constraint enforced by the optimizer."""

    HARD = "hard"
    SOFT = "soft"


class ConstraintStatus(StrEnum):
    """The current evaluation status of one optimization constraint."""

    PASSED = "passed"
    VIOLATED = "violated"
    AT_RISK = "at_risk"
    UNVERIFIED = "unverified"


class OptimizationConstraint(BaseModel):
    """A guardrail that constrains optimization proposals and evaluations."""

    model_config = ConfigDict(frozen=True)

    target: str = Field(min_length=1)
    severity: ConstraintSeverity = ConstraintSeverity.HARD
    minimum_value: float | None = None
    maximum_value: float | None = None
    unit: str | None = None
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> OptimizationConstraint:
        """Require at least one bound and keep bounds ordered."""
        if self.minimum_value is None and self.maximum_value is None:
            msg = "At least one constraint bound must be provided."
            raise ValueError(msg)

        if (
            self.minimum_value is not None
            and self.maximum_value is not None
            and self.minimum_value > self.maximum_value
        ):
            msg = "The minimum constraint bound cannot exceed the maximum bound."
            raise ValueError(msg)

        return self


class ConstraintEvaluation(BaseModel):
    """Structured evaluation result for one optimization constraint."""

    model_config = ConfigDict(frozen=True)

    constraint: OptimizationConstraint
    status: ConstraintStatus
    current_value: float | None = None
    passed: bool
    summary: str = Field(min_length=1)
    violation_amount: float | None = None


class ConstraintEvaluator:
    """Evaluate reusable optimization constraints against metrics and hypotheses."""

    def evaluate_current(self, decision_input: DecisionInput) -> tuple[ConstraintEvaluation, ...]:
        """Evaluate the current building metrics against all configured constraints."""
        return tuple(
            self._evaluate_constraint(decision_input, constraint)
            for constraint in decision_input.constraints
        )

    def evaluate_hypothesis(
        self,
        decision_input: DecisionInput,
        hypothesis: EngineeringHypothesis,
    ) -> tuple[ConstraintEvaluation, ...]:
        """Project how one hypothesis may pressure the configured constraints."""
        evaluations: list[ConstraintEvaluation] = []
        for current_evaluation in self.evaluate_current(decision_input):
            if current_evaluation.status in {
                ConstraintStatus.UNVERIFIED,
                ConstraintStatus.VIOLATED,
            }:
                evaluations.append(current_evaluation)
                continue

            if self._creates_constraint_risk(current_evaluation.constraint, hypothesis):
                evaluations.append(
                    current_evaluation.model_copy(
                        update={
                            "status": ConstraintStatus.AT_RISK,
                            "passed": False,
                            "summary": (
                                f"{hypothesis.title} may place pressure on the "
                                f"{current_evaluation.constraint.target} constraint."
                            ),
                        }
                    )
                )
                continue

            evaluations.append(current_evaluation)

        return tuple(evaluations)

    def _evaluate_constraint(
        self,
        decision_input: DecisionInput,
        constraint: OptimizationConstraint,
    ) -> ConstraintEvaluation:
        """Evaluate one constraint against the current normalized simulation metrics."""
        current_value = resolve_metric_value(decision_input.current_metrics, constraint.target)
        unit = constraint.unit or resolve_metric_unit(
            decision_input.current_metrics, constraint.target
        )
        if current_value is None:
            return ConstraintEvaluation(
                constraint=constraint,
                status=ConstraintStatus.UNVERIFIED,
                current_value=None,
                passed=False,
                summary=f"{constraint.target} could not be verified against the current metrics.",
            )

        minimum_violation = (
            constraint.minimum_value - current_value
            if constraint.minimum_value is not None and current_value < constraint.minimum_value
            else None
        )
        maximum_violation = (
            current_value - constraint.maximum_value
            if constraint.maximum_value is not None and current_value > constraint.maximum_value
            else None
        )
        violation_amount = minimum_violation or maximum_violation
        if violation_amount is not None:
            return ConstraintEvaluation(
                constraint=constraint,
                status=ConstraintStatus.VIOLATED,
                current_value=current_value,
                passed=False,
                summary=(
                    f"{constraint.target} violates its configured bounds at {current_value:.2f} "
                    f"{unit or ''}."
                ).strip(),
                violation_amount=round(violation_amount, 2),
            )

        return ConstraintEvaluation(
            constraint=constraint,
            status=ConstraintStatus.PASSED,
            current_value=current_value,
            passed=True,
            summary=(
                f"{constraint.target} is within the configured bounds at {current_value:.2f} "
                f"{unit or ''}."
            ).strip(),
        )

    def _creates_constraint_risk(
        self,
        constraint: OptimizationConstraint,
        hypothesis: EngineeringHypothesis,
    ) -> bool:
        """Return whether one hypothesis may place pressure on a validated constraint."""
        from ecoloop_ai.optimization.hypothesis import ImpactDirection

        target = constraint.target.lower()
        if self._is_comfort_constraint(target):
            return hypothesis.expected_comfort_impact.direction in {
                ImpactDirection.DECREASE,
                ImpactDirection.MIXED,
            }

        if self._is_carbon_constraint(target):
            return self._impact_worsens_bound(
                hypothesis.expected_carbon_impact.direction,
                constraint,
            )

        if self._is_cost_constraint(target):
            return self._impact_worsens_bound(
                hypothesis.expected_cost_impact.direction,
                constraint,
            )

        return self._impact_worsens_bound(hypothesis.expected_energy_impact.direction, constraint)

    @staticmethod
    def _impact_worsens_bound(
        direction: object,
        constraint: OptimizationConstraint,
    ) -> bool:
        """Return whether one impact direction risks violating a numeric bound."""
        direction_value = getattr(direction, "value", str(direction))
        if direction_value == "increase" and constraint.maximum_value is not None:
            return True

        if direction_value == "decrease" and constraint.minimum_value is not None:
            return True

        return direction_value == "mixed"

    @staticmethod
    def _is_comfort_constraint(target: str) -> bool:
        """Return whether one target name refers to comfort-related metrics."""
        return any(
            token in target for token in ("comfort", "ppd", "pmv", "temperature", "humidity")
        )

    @staticmethod
    def _is_carbon_constraint(target: str) -> bool:
        """Return whether one target name refers to carbon metrics."""
        return "carbon" in target or "co2" in target

    @staticmethod
    def _is_cost_constraint(target: str) -> bool:
        """Return whether one target name refers to cost metrics."""
        return "cost" in target or "usd" in target


__all__ = [
    "ConstraintEvaluation",
    "ConstraintEvaluator",
    "ConstraintSeverity",
    "ConstraintStatus",
    "OptimizationConstraint",
]
