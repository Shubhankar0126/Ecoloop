"""Natural-language goal interpretation for the optimization reasoning layer."""

from __future__ import annotations

import re

from ecoloop_ai.optimization.config import OptimizationConfig
from ecoloop_ai.optimization.constraints import (
    ConstraintSeverity,
    OptimizationConstraint,
)
from ecoloop_ai.optimization.exceptions import GoalInterpretationError
from ecoloop_ai.optimization.models import GoalInterpretation
from ecoloop_ai.optimization.objectives import (
    ObjectivePriority,
    OptimizationGoal,
    OptimizationObjective,
    OptimizationObjectiveKind,
    default_direction,
    default_metric_name,
)


class GoalInterpreter:
    """Normalize natural-language optimization goals into domain models."""

    _whole_building_energy_phrases: tuple[str, ...] = (
        "total site energy",
        "site energy",
        "whole building energy",
        "building energy",
    )
    _specific_energy_objectives: frozenset[OptimizationObjectiveKind] = frozenset(
        {
            OptimizationObjectiveKind.HVAC_ENERGY,
            OptimizationObjectiveKind.COOLING_ENERGY,
            OptimizationObjectiveKind.HEATING_ENERGY,
            OptimizationObjectiveKind.LIGHTING_ENERGY,
            OptimizationObjectiveKind.VENTILATION_EFFICIENCY,
            OptimizationObjectiveKind.PEAK_DEMAND,
        }
    )
    _objective_keywords: tuple[tuple[str, OptimizationObjectiveKind], ...] = (
        ("peak demand", OptimizationObjectiveKind.PEAK_DEMAND),
        ("hvac", OptimizationObjectiveKind.HVAC_ENERGY),
        ("cooling", OptimizationObjectiveKind.COOLING_ENERGY),
        ("heating", OptimizationObjectiveKind.HEATING_ENERGY),
        ("comfort", OptimizationObjectiveKind.THERMAL_COMFORT),
        ("carbon", OptimizationObjectiveKind.CARBON_EMISSIONS),
        ("emissions", OptimizationObjectiveKind.CARBON_EMISSIONS),
        ("cost", OptimizationObjectiveKind.OPERATING_COST),
        ("lighting", OptimizationObjectiveKind.LIGHTING_ENERGY),
        ("ventilation", OptimizationObjectiveKind.VENTILATION_EFFICIENCY),
        ("energy", OptimizationObjectiveKind.TOTAL_SITE_ENERGY),
    )

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize the goal interpreter with injected optimization policy."""
        self._config = config or OptimizationConfig()

    def interpret(self, goal_text: str) -> GoalInterpretation:
        """Interpret a natural-language optimization goal into structured models."""
        normalized_goal = " ".join(goal_text.strip().split())
        if not normalized_goal:
            raise GoalInterpretationError(
                "The optimization goal text cannot be empty.",
            )

        lowered = normalized_goal.casefold()
        detected_kinds = self._detect_objective_kinds(lowered)
        diagnostics: list[str] = []
        if not detected_kinds:
            detected_kinds = (OptimizationObjectiveKind.CUSTOM,)
            diagnostics.append(
                "No known objective keywords were detected; a custom objective was created."
            )

        target_percent = self._parse_percentage(lowered)
        constraints, constraint_diagnostics = self._parse_constraints(lowered)
        diagnostics.extend(constraint_diagnostics)
        objectives = tuple(
            self._build_objective(
                kind=kind,
                priority=ObjectivePriority.HIGH if index == 0 else ObjectivePriority.MEDIUM,
                target_percent=target_percent,
            )
            for index, kind in enumerate(detected_kinds)
        )
        goal = OptimizationGoal(
            summary=normalized_goal,
            objectives=objectives,
            success_criteria=tuple(self._success_criterion(item) for item in objectives),
            business_constraints=tuple(
                constraint.rationale or f"Maintain {constraint.target} within bounds."
                for constraint in constraints
            ),
            source_text=normalized_goal,
        )
        return GoalInterpretation(
            source_text=normalized_goal,
            goal=goal,
            constraints=constraints,
            diagnostics=tuple(diagnostics),
        )

    def _detect_objective_kinds(self, lowered_goal: str) -> tuple[OptimizationObjectiveKind, ...]:
        """Detect the ordered optimization objective kinds mentioned in one goal string."""
        detected: list[OptimizationObjectiveKind] = []
        for keyword, kind in self._objective_keywords:
            if self._is_guardrail_only_reference(lowered_goal, kind):
                continue

            if keyword in lowered_goal and kind not in detected:
                detected.append(kind)

        if (
            OptimizationObjectiveKind.TOTAL_SITE_ENERGY in detected
            and any(kind in self._specific_energy_objectives for kind in detected)
            and not any(
                phrase in lowered_goal for phrase in self._whole_building_energy_phrases
            )
        ):
            detected = [
                kind
                for kind in detected
                if kind is not OptimizationObjectiveKind.TOTAL_SITE_ENERGY
            ]

        return tuple(detected)

    @staticmethod
    def _is_guardrail_only_reference(
        lowered_goal: str,
        kind: OptimizationObjectiveKind,
    ) -> bool:
        """Return whether a keyword appears only as a non-increase guardrail."""
        if kind is OptimizationObjectiveKind.OPERATING_COST:
            return (
                any(
                    phrase in lowered_goal
                    for phrase in ("without increasing cost", "cost cannot increase")
                )
                and not any(
                    phrase in lowered_goal
                    for phrase in (
                        "reduce cost",
                        "lower cost",
                        "decrease cost",
                        "minimize cost",
                        "optimize cost",
                    )
                )
            )

        if kind is OptimizationObjectiveKind.CARBON_EMISSIONS:
            return (
                any(
                    phrase in lowered_goal
                    for phrase in (
                        "without increasing carbon",
                        "carbon cannot increase",
                        "without increasing emissions",
                        "emissions cannot increase",
                    )
                )
                and not any(
                    phrase in lowered_goal
                    for phrase in (
                        "reduce carbon",
                        "lower carbon",
                        "decrease carbon",
                        "minimize carbon",
                        "reduce emissions",
                        "lower emissions",
                        "decrease emissions",
                        "minimize emissions",
                    )
                )
            )

        return False

    def _build_objective(
        self,
        *,
        kind: OptimizationObjectiveKind,
        priority: ObjectivePriority,
        target_percent: float | None,
    ) -> OptimizationObjective:
        """Build one structured objective definition from interpreted goal metadata."""
        reduction_target: float | None = (
            target_percent or self._config.reasoning.default_target_reduction_percent
        )
        if default_direction(kind).value == "balance":
            reduction_target = None

        return OptimizationObjective(
            kind=kind,
            metric_name=default_metric_name(kind),
            direction=default_direction(kind),
            weight=1.0,
            priority=priority,
            target_reduction_percent=reduction_target,
            tolerance=self._config.reasoning.default_objective_tolerance,
            rationale=f"Derived from the natural-language goal for {kind.value}.",
        )

    def _parse_percentage(self, lowered_goal: str) -> float | None:
        """Extract a percentage target from the goal when one is present."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", lowered_goal)
        if match is None:
            return None

        return float(match.group(1))

    def _parse_constraints(
        self,
        lowered_goal: str,
    ) -> tuple[tuple[OptimizationConstraint, ...], tuple[str, ...]]:
        """Extract reusable constraints and diagnostics from the natural-language goal."""
        constraints: list[OptimizationConstraint] = []
        diagnostics: list[str] = []
        if any(
            phrase in lowered_goal
            for phrase in ("maintain comfort", "maintaining comfort", "preserve comfort")
        ):
            constraints.append(
                OptimizationConstraint(
                    target="average_ppd_percent",
                    severity=ConstraintSeverity.HARD,
                    maximum_value=10.0,
                    unit="%",
                    rationale="Maintain thermal comfort within acceptable bounds.",
                )
            )

        if "carbon cannot increase" in lowered_goal or "without increasing carbon" in lowered_goal:
            diagnostics.append(
                "Carbon non-increase was retained as a textual guardrail because "
                "it requires a baseline reference."
            )

        if "cost cannot increase" in lowered_goal or "without increasing cost" in lowered_goal:
            diagnostics.append(
                "Cost non-increase was retained as a textual guardrail because "
                "it requires a baseline reference."
            )

        return tuple(constraints), tuple(diagnostics)

    @staticmethod
    def _success_criterion(objective: OptimizationObjective) -> str:
        """Render one human-readable success criterion from an objective definition."""
        if objective.target_reduction_percent is not None:
            return (
                f"Achieve a {objective.target_reduction_percent:.1f}% "
                f"{objective.direction.value} target for {objective.kind.value}."
            )

        return f"Improve {objective.kind.value} according to its configured direction."


__all__ = ["GoalInterpreter"]
