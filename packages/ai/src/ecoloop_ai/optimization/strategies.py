"""Optimization strategy contracts and interchangeable reasoning strategies."""

from __future__ import annotations

from enum import StrEnum
from random import Random
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.exceptions import StrategyResolutionError
from ecoloop_ai.optimization.hypothesis import HypothesisCategory, HypothesisEvaluation, RiskLevel
from ecoloop_ai.optimization.objectives import OptimizationObjectiveKind

if TYPE_CHECKING:
    from ecoloop_ai.optimization.config import OptimizationConfig
    from ecoloop_ai.optimization.models import DecisionInput, ObjectiveEvaluation, StrategyDecision


class RiskTolerance(StrEnum):
    """How much operational risk a strategy is willing to accept."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OptimizationAggressiveness(StrEnum):
    """How aggressively a strategy is willing to search for improvements."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OptimizationStrategyKind(StrEnum):
    """Supported high-level optimization strategy profiles."""

    AI_GUIDED = "ai_guided"
    GREEDY = "greedy"
    RULE_BASED = "rule_based"
    HILL_CLIMBING = "hill_climbing"
    RANDOM_EXPLORATION = "random_exploration"
    BASELINE_PRESERVING = "baseline_preserving"
    COMFORT_FIRST = "comfort_first"
    ENERGY_FIRST = "energy_first"
    COST_FIRST = "cost_first"
    EMISSIONS_FIRST = "emissions_first"
    BALANCED = "balanced"


class OptimizationStrategyProfile(BaseModel):
    """A reusable strategy profile that describes how the optimizer should behave."""

    model_config = ConfigDict(frozen=True)

    kind: OptimizationStrategyKind
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    aggressiveness: OptimizationAggressiveness = OptimizationAggressiveness.MEDIUM
    preferred_focus_areas: tuple[str, ...] = ()
    selection_limit: int | None = Field(default=None, ge=1, le=10)


class StrategyContract(Protocol):
    """Framework-independent contract shared by all optimization strategies."""

    profile: OptimizationStrategyProfile

    def hypothesis_categories(
        self,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
    ) -> tuple[HypothesisCategory, ...]:
        """Return the preferred hypothesis categories for the current goal."""

    def generation_limit(self) -> int:
        """Return the maximum number of generated hypotheses this strategy wants."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return the prioritized hypothesis evaluations for the strategy."""

    def should_stop(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        prioritized_hypotheses: tuple[HypothesisEvaluation, ...],
    ) -> bool:
        """Return whether exploration should stop before simulation."""

    def decide(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> StrategyDecision:
        """Create the strategy decision for the current reasoning step."""


class BaseStrategy:
    """Shared reusable logic for interchangeable optimization strategies."""

    def __init__(
        self,
        *,
        config: OptimizationConfig,
        profile: OptimizationStrategyProfile,
        random_state: Random | None = None,
    ) -> None:
        self._config = config
        self.profile = profile
        self._random_state = random_state or Random(config.reasoning.random_seed)

    def hypothesis_categories(
        self,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
    ) -> tuple[HypothesisCategory, ...]:
        """Return the preferred hypothesis categories for the current goal."""
        ordered_categories: list[HypothesisCategory] = []
        for evaluation in objective_evaluations:
            for category in _objective_categories(evaluation.objective.kind):
                if category not in ordered_categories:
                    ordered_categories.append(category)

        if not ordered_categories:
            return tuple(HypothesisCategory)

        return tuple(ordered_categories)

    def generation_limit(self) -> int:
        """Return the maximum number of generated hypotheses this strategy wants."""
        return min(
            self._config.reasoning.maximum_generated_hypotheses,
            max(
                self.profile.selection_limit or self._config.reasoning.strategy_selection_limit,
                self._config.reasoning.strategy_selection_limit,
            ),
        )

    def selection_limit(self) -> int:
        """Return the number of hypotheses the strategy wants to carry forward."""
        return min(
            self.profile.selection_limit or self._config.reasoning.strategy_selection_limit,
            self._config.reasoning.strategy_selection_limit,
        )

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return the prioritized hypothesis evaluations for the strategy."""
        return tuple(
            sorted(
                hypothesis_evaluations,
                key=lambda item: (
                    item.accepted,
                    item.overall_score.value,
                    item.objective_alignment_score,
                    -_risk_rank(item.risk_assessment.level),
                ),
                reverse=True,
            )
        )

    def should_stop(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        prioritized_hypotheses: tuple[HypothesisEvaluation, ...],
    ) -> bool:
        """Return whether exploration should stop before simulation."""
        del decision_input
        if objective_evaluations and all(item.satisfied for item in objective_evaluations):
            return True

        return bool(prioritized_hypotheses) and (
            prioritized_hypotheses[0].overall_score.value
            >= self._config.reasoning.satisfaction_score_threshold
        )

    def decide(
        self,
        decision_input: DecisionInput,
        objective_evaluations: tuple[ObjectiveEvaluation, ...],
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> StrategyDecision:
        """Create the strategy decision for the current reasoning step."""
        from ecoloop_ai.optimization.models import StrategyDecision

        prioritized = self.prioritize(hypothesis_evaluations)
        selection_limit = min(self.selection_limit(), len(prioritized))
        selected = prioritized[:selection_limit]
        selection_confidence = 0.0
        if selected:
            selection_confidence = round(
                sum(item.hypothesis.confidence for item in selected) / len(selected),
                2,
            )
        return StrategyDecision(
            strategy_kind=self.profile.kind,
            prioritized_hypothesis_ids=tuple(item.hypothesis.hypothesis_id for item in prioritized),
            selected_hypothesis_ids=tuple(item.hypothesis.hypothesis_id for item in selected),
            stop_exploring=self.should_stop(decision_input, objective_evaluations, prioritized),
            aggressiveness=self.profile.aggressiveness,
            rationale=self._decision_rationale(selected),
            selection_confidence=selection_confidence,
        )

    def _decision_rationale(self, selected: tuple[HypothesisEvaluation, ...]) -> str:
        """Return a concise rationale for the strategy outcome."""
        if not selected:
            return f"{self.profile.title} did not identify a viable hypothesis candidate."

        titles = ", ".join(item.hypothesis.title for item in selected)
        return f"{self.profile.title} prioritized {titles}."


class GreedyStrategy(BaseStrategy):
    """Select the highest-scoring candidate with the strongest direct impact."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return greedily prioritized hypothesis evaluations."""
        return tuple(
            sorted(
                hypothesis_evaluations,
                key=lambda item: (
                    item.overall_score.value,
                    item.objective_alignment_score,
                    item.hypothesis.confidence,
                    -_risk_rank(item.risk_assessment.level),
                ),
                reverse=True,
            )
        )


class RuleBasedStrategy(BaseStrategy):
    """Prefer viable, low-risk hypotheses that follow explicit guardrails."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return rule-based prioritized hypothesis evaluations."""
        return tuple(
            sorted(
                hypothesis_evaluations,
                key=lambda item: (
                    item.accepted,
                    -_risk_rank(item.risk_assessment.level),
                    item.hypothesis.confidence,
                    item.overall_score.value,
                ),
                reverse=True,
            )
        )


class HillClimbingStrategy(BaseStrategy):
    """Prefer incremental low-risk improvements before aggressive exploration."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return conservatively prioritized hypothesis evaluations."""
        return tuple(
            sorted(
                hypothesis_evaluations,
                key=lambda item: (
                    item.accepted,
                    -_risk_rank(item.risk_assessment.level),
                    item.objective_alignment_score,
                    item.overall_score.value,
                ),
                reverse=True,
            )
        )


class AIGuidedStrategy(BaseStrategy):
    """Use weighted scoring and confidence to mimic structured AI guidance."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return weighted-confidence prioritized hypothesis evaluations."""
        return tuple(
            sorted(
                hypothesis_evaluations,
                key=lambda item: (
                    item.overall_score.value * 0.6
                    + item.objective_alignment_score * 0.3
                    + item.hypothesis.confidence * 10.0
                    - _risk_rank(item.risk_assessment.level) * 5.0
                ),
                reverse=True,
            )
        )


class RandomExplorationStrategy(BaseStrategy):
    """Deliberately diversify candidate ordering to widen the search space."""

    def prioritize(
        self,
        hypothesis_evaluations: tuple[HypothesisEvaluation, ...],
    ) -> tuple[HypothesisEvaluation, ...]:
        """Return randomly shuffled hypothesis evaluations."""
        items = list(hypothesis_evaluations)
        self._random_state.shuffle(items)
        return tuple(
            sorted(
                items,
                key=lambda item: (item.accepted, -_risk_rank(item.risk_assessment.level)),
                reverse=True,
            )
        )


class StrategyRegistry:
    """Resolve optimization strategies without exposing implementation details."""

    def __init__(
        self,
        *,
        config: OptimizationConfig | None = None,
        random_state: Random | None = None,
    ) -> None:
        if config is None:
            from ecoloop_ai.optimization.config import OptimizationConfig as ConfigModel

            config = ConfigModel()

        self._config = config
        self._random_state = random_state or Random(self._config.reasoning.random_seed)

    def resolve(self, kind: OptimizationStrategyKind) -> StrategyContract:
        """Resolve the configured optimization strategy."""
        if kind is OptimizationStrategyKind.GREEDY:
            return GreedyStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Greedy Strategy",
                    summary="Take the highest-scoring direct improvement first.",
                    risk_tolerance=RiskTolerance.HIGH,
                    aggressiveness=OptimizationAggressiveness.HIGH,
                    selection_limit=1,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.RULE_BASED:
            return RuleBasedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Rule-Based Strategy",
                    summary="Prefer explicitly viable, guardrail-compliant changes.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.MEDIUM,
                    selection_limit=2,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.HILL_CLIMBING:
            return HillClimbingStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Hill-Climbing Strategy",
                    summary="Prefer incremental low-risk improvements before larger steps.",
                    risk_tolerance=RiskTolerance.LOW,
                    aggressiveness=OptimizationAggressiveness.LOW,
                    selection_limit=1,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.RANDOM_EXPLORATION:
            return RandomExplorationStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Random Exploration Strategy",
                    summary="Diversify candidate order to widen the search surface.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.HIGH,
                    selection_limit=2,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.AI_GUIDED:
            return AIGuidedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="AI-Guided Strategy",
                    summary="Use weighted reasoning, confidence, and risk to choose candidates.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.MEDIUM,
                    selection_limit=3,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.BASELINE_PRESERVING:
            return HillClimbingStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Baseline-Preserving Strategy",
                    summary="Favor small, reversible changes that preserve baseline behavior.",
                    risk_tolerance=RiskTolerance.LOW,
                    aggressiveness=OptimizationAggressiveness.LOW,
                    selection_limit=1,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.COMFORT_FIRST:
            return RuleBasedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Comfort-First Strategy",
                    summary="Prefer comfort-preserving changes before aggressive savings.",
                    risk_tolerance=RiskTolerance.LOW,
                    aggressiveness=OptimizationAggressiveness.LOW,
                    preferred_focus_areas=("comfort", "ventilation"),
                    selection_limit=2,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.ENERGY_FIRST:
            return GreedyStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Energy-First Strategy",
                    summary="Maximize direct energy savings potential.",
                    risk_tolerance=RiskTolerance.HIGH,
                    aggressiveness=OptimizationAggressiveness.HIGH,
                    preferred_focus_areas=("hvac", "lighting"),
                    selection_limit=1,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.COST_FIRST:
            return RuleBasedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Cost-First Strategy",
                    summary="Prefer hypotheses with strong cost reductions and manageable risk.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.MEDIUM,
                    preferred_focus_areas=("schedules", "hvac"),
                    selection_limit=2,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.EMISSIONS_FIRST:
            return RuleBasedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Emissions-First Strategy",
                    summary="Prefer hypotheses with direct carbon reduction potential.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.MEDIUM,
                    preferred_focus_areas=("hvac", "ventilation"),
                    selection_limit=2,
                ),
                random_state=self._random_state,
            )

        if kind is OptimizationStrategyKind.BALANCED:
            return AIGuidedStrategy(
                config=self._config,
                profile=OptimizationStrategyProfile(
                    kind=kind,
                    title="Balanced Strategy",
                    summary="Balance savings potential, risk, and comfort considerations.",
                    risk_tolerance=RiskTolerance.MEDIUM,
                    aggressiveness=OptimizationAggressiveness.MEDIUM,
                    selection_limit=3,
                ),
                random_state=self._random_state,
            )

        raise StrategyResolutionError(
            context={"strategy_kind": kind.value},
        )


def _risk_rank(level: RiskLevel) -> int:
    """Convert semantic risk levels into stable numeric ranking."""
    return {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }[level]


def _objective_categories(kind: OptimizationObjectiveKind) -> tuple[HypothesisCategory, ...]:
    """Map one objective kind onto the most relevant hypothesis categories."""
    return {
        OptimizationObjectiveKind.TOTAL_SITE_ENERGY: (
            HypothesisCategory.SCHEDULES,
            HypothesisCategory.HVAC,
            HypothesisCategory.LIGHTING,
        ),
        OptimizationObjectiveKind.HVAC_ENERGY: (
            HypothesisCategory.HVAC,
            HypothesisCategory.CONTROLS,
            HypothesisCategory.SCHEDULES,
        ),
        OptimizationObjectiveKind.COOLING_ENERGY: (
            HypothesisCategory.HVAC,
            HypothesisCategory.CONTROLS,
        ),
        OptimizationObjectiveKind.HEATING_ENERGY: (
            HypothesisCategory.HVAC,
            HypothesisCategory.CONTROLS,
        ),
        OptimizationObjectiveKind.THERMAL_COMFORT: (
            HypothesisCategory.CONTROLS,
            HypothesisCategory.VENTILATION,
        ),
        OptimizationObjectiveKind.CARBON_EMISSIONS: (
            HypothesisCategory.HVAC,
            HypothesisCategory.SCHEDULES,
        ),
        OptimizationObjectiveKind.OPERATING_COST: (
            HypothesisCategory.SCHEDULES,
            HypothesisCategory.HVAC,
        ),
        OptimizationObjectiveKind.PEAK_DEMAND: (
            HypothesisCategory.HVAC,
            HypothesisCategory.EQUIPMENT,
        ),
        OptimizationObjectiveKind.LIGHTING_ENERGY: (
            HypothesisCategory.LIGHTING,
            HypothesisCategory.SCHEDULES,
        ),
        OptimizationObjectiveKind.VENTILATION_EFFICIENCY: (
            HypothesisCategory.VENTILATION,
            HypothesisCategory.CONTROLS,
        ),
    }.get(kind, tuple(HypothesisCategory))


__all__ = [
    "AIGuidedStrategy",
    "BaseStrategy",
    "GreedyStrategy",
    "HillClimbingStrategy",
    "OptimizationAggressiveness",
    "OptimizationStrategyKind",
    "OptimizationStrategyProfile",
    "RandomExplorationStrategy",
    "RiskTolerance",
    "RuleBasedStrategy",
    "StrategyContract",
    "StrategyRegistry",
]
