"""Pre-simulation risk assessment for optimization hypotheses."""

from __future__ import annotations

from ecoloop_ai.optimization.config import OptimizationConfig
from ecoloop_ai.optimization.constraints import (
    ConstraintEvaluation,
    ConstraintSeverity,
    ConstraintStatus,
)
from ecoloop_ai.optimization.hypothesis import (
    EngineeringHypothesis,
    RiskAssessment,
    RiskLevel,
)


class RiskAssessor:
    """Assess pre-simulation operational risk for one engineering hypothesis."""

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize the risk assessor with injected optimization policy."""
        self._config = config or OptimizationConfig()

    def assess(
        self,
        hypothesis: EngineeringHypothesis,
        *,
        constraint_evaluations: tuple[ConstraintEvaluation, ...] = (),
    ) -> RiskAssessment:
        """Assess the operational risk associated with one hypothesis."""
        risk_score = _risk_level_rank(hypothesis.estimated_risk)
        factors: list[str] = []
        mitigations: list[str] = []

        if hypothesis.confidence < max(0.5, self._config.reasoning.minimum_hypothesis_confidence):
            risk_score += 1
            factors.append("Hypothesis confidence is still limited.")
            mitigations.append("Collect more baseline evidence before simulation.")

        if hypothesis.expected_comfort_impact.direction.value in {"decrease", "mixed"}:
            risk_score += 1
            factors.append("Comfort could degrade if the change is too aggressive.")
            mitigations.append("Validate occupied comfort metrics before any rollout.")

        if hypothesis.expected_cost_impact.direction.value == "increase":
            risk_score += 1
            factors.append("Operating cost could increase before savings are verified.")
            mitigations.append("Review tariff exposure and time-of-use effects first.")

        if hypothesis.expected_carbon_impact.direction.value == "increase":
            risk_score += 1
            factors.append(
                "Carbon emissions could increase if energy source mix shifts unfavorably."
            )
            mitigations.append("Check emissions intensity before prioritizing this change.")

        if any(
            item.status in {ConstraintStatus.VIOLATED, ConstraintStatus.AT_RISK}
            and item.constraint.severity is ConstraintSeverity.HARD
            for item in constraint_evaluations
        ):
            risk_score += 2
            factors.append("One or more hard constraints may be violated.")
            mitigations.append("Rework the hypothesis so hard constraints remain protected.")

        if hypothesis.category.value in {"equipment", "hvac"}:
            risk_score += 1
            factors.append("The affected system could require tighter operational coordination.")
            mitigations.append(
                "Review system sequencing and override interactions before simulation."
            )

        level = _rank_to_risk_level(risk_score)
        explanation = (
            " ; ".join(factors)
            if factors
            else "No material pre-simulation risks were detected for the current hypothesis."
        )
        return RiskAssessment(
            hypothesis_id=hypothesis.hypothesis_id,
            level=level,
            explanation=explanation,
            mitigation_suggestions=tuple(dict.fromkeys(mitigations)),
            triggering_factors=tuple(factors),
            constraint_evaluations=constraint_evaluations,
        )


def _risk_level_rank(level: RiskLevel) -> int:
    """Convert a semantic risk level into a stable numeric score."""
    return {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }[level]


def _rank_to_risk_level(rank: int) -> RiskLevel:
    """Map a numeric risk rank back onto the public semantic risk levels."""
    if rank <= 0:
        return RiskLevel.LOW

    if rank == 1:
        return RiskLevel.MEDIUM

    if rank == 2:
        return RiskLevel.HIGH

    return RiskLevel.CRITICAL


__all__ = ["RiskAssessor"]
