from __future__ import annotations

from random import Random

import pytest

from ecoloop_ai.models import BuildingContext
from ecoloop_ai.optimization import (
    BuildingMetadata,
    ConstraintEvaluator,
    ConstraintSeverity,
    ConstraintStatus,
    DecisionInput,
    DecisionSummary,
    EngineeringHypothesis,
    GoalInterpretation,
    GoalInterpretationError,
    GoalInterpreter,
    HypothesisCategory,
    HypothesisEngine,
    HypothesisGenerationError,
    ImpactDirection,
    ImpactEstimate,
    ImpactMagnitude,
    ObjectivePriority,
    ObjectiveRegistry,
    OptimizationConfig,
    OptimizationConstraint,
    OptimizationDirection,
    OptimizationEngine,
    OptimizationGoal,
    OptimizationObjective,
    OptimizationObjectiveKind,
    OptimizationPlanner,
    OptimizationReasoningSettings,
    OptimizationRequest,
    OptimizationSession,
    OptimizationStrategyKind,
    OptimizationWorkflow,
    RiskAssessor,
    RiskLevel,
    StrategyRegistry,
    WeatherMetadata,
)
from ecoloop_ai.optimization.metrics import resolve_metric_unit, resolve_metric_value
from ecoloop_energyplus import (
    ComfortMetrics,
    EnergyMetrics,
    HVACMetrics,
    SimulationMetrics,
    SimulationMetricValue,
    WeatherMetrics,
    ZoneMetrics,
)


def _metrics(*, comfort_ppd: float = 8.0) -> SimulationMetrics:
    return SimulationMetrics(
        energy=EnergyMetrics(
            total_site_energy_kwh=950.0,
            electricity_consumption_kwh=520.0,
        ),
        hvac=HVACMetrics(
            heating_energy_kwh=110.0,
            cooling_energy_kwh=190.0,
            hvac_energy_kwh=300.0,
            equipment_loads_kwh=85.0,
        ),
        comfort=ComfortMetrics(
            average_zone_temperature_celsius=22.3,
            average_zone_humidity_percent=45.0,
            average_pmv=0.2,
            average_ppd_percent=comfort_ppd,
        ),
        weather=WeatherMetrics(
            average_outdoor_dry_bulb_celsius=31.0,
            average_outdoor_relative_humidity_percent=58.0,
        ),
        zones=(
            ZoneMetrics(
                zone_name="OPEN OFFICE",
                mean_air_temperature_celsius=22.4,
                mean_relative_humidity_percent=44.0,
                thermal_comfort_pmv=0.2,
                thermal_comfort_ppd_percent=comfort_ppd,
            ),
        ),
    )


def _metrics_with_values(*, comfort_ppd: float = 8.0) -> SimulationMetrics:
    return _metrics(comfort_ppd=comfort_ppd).model_copy(
        update={
            "values": {
                "carbon_emissions_kgco2e": SimulationMetricValue(
                    value=120.0,
                    unit="kgCO2e",
                ),
                "operating_cost_usd": SimulationMetricValue(value=540.0, unit="USD"),
                "peak_demand_kw": SimulationMetricValue(value=95.0, unit="kW"),
                "lighting_energy_kwh": SimulationMetricValue(value=140.0, unit="kWh"),
                "ventilation_efficiency_percent": SimulationMetricValue(
                    value=82.0,
                    unit="%",
                ),
                "custom_goal_score": SimulationMetricValue(value=70.0, unit="score"),
                "system_availability_percent": SimulationMetricValue(value=98.0, unit="%"),
            }
        }
    )


def _interpreted_goal() -> GoalInterpretation:
    interpreter = GoalInterpreter()
    return interpreter.interpret("Reduce HVAC energy by 20% while maintaining comfort.")


def _decision_input(*, comfort_ppd: float = 8.0) -> DecisionInput:
    interpreted = _interpreted_goal()
    return DecisionInput(
        current_metrics=_metrics(comfort_ppd=comfort_ppd),
        goal=interpreted.goal,
        constraints=interpreted.constraints,
        building_metadata=BuildingMetadata(
            building_name="HQ Tower",
            building_type="Office",
            floor_area_m2=18000.0,
            primary_hvac_system="VAV with chilled water plant",
        ),
        weather_metadata=WeatherMetadata(
            climate_zone="Warm-Humid",
            season="summer",
            peak_cooling_month="July",
        ),
        building_context=BuildingContext(building_name="HQ Tower"),
    )


def _decision_input_for_goal(
    goal: OptimizationGoal,
    *,
    constraints: tuple[OptimizationConstraint, ...] = (),
    metrics: SimulationMetrics | None = None,
) -> DecisionInput:
    base = _decision_input()
    return base.model_copy(
        update={
            "current_metrics": metrics or _metrics_with_values(),
            "goal": goal,
            "constraints": constraints,
        }
    )


def test_goal_interpreter_builds_structured_goal_and_constraints() -> None:
    interpretation = GoalInterpreter().interpret(
        "Reduce HVAC energy by 20% while maintaining comfort and without increasing carbon."
    )

    assert interpretation.goal.objectives[0].kind is OptimizationObjectiveKind.HVAC_ENERGY
    assert interpretation.goal.objectives[0].target_reduction_percent == pytest.approx(20.0)
    assert interpretation.goal.objectives[0].priority is ObjectivePriority.HIGH
    assert interpretation.constraints[0].target == "average_ppd_percent"
    assert "baseline reference" in interpretation.diagnostics[0]


def test_goal_interpreter_rejects_empty_input_and_deduplicates_generic_energy() -> None:
    interpreter = GoalInterpreter()

    with pytest.raises(GoalInterpretationError):
        interpreter.interpret("   ")

    hvac_goal = interpreter.interpret("Reduce HVAC energy by 15% without increasing cost.")
    site_goal = interpreter.interpret("Reduce total site energy by 10%.")

    assert tuple(item.kind for item in hvac_goal.goal.objectives) == (
        OptimizationObjectiveKind.HVAC_ENERGY,
    )
    assert "cost non-increase" in hvac_goal.diagnostics[0].casefold()
    assert tuple(item.kind for item in site_goal.goal.objectives) == (
        OptimizationObjectiveKind.TOTAL_SITE_ENERGY,
    )


def test_goal_interpreter_falls_back_to_custom_objective() -> None:
    interpretation = GoalInterpreter().interpret("Make the building friendlier to occupants.")

    assert interpretation.goal.objectives[0].kind is OptimizationObjectiveKind.CUSTOM
    assert "custom objective" in interpretation.diagnostics[0].casefold()


def test_objective_registry_scores_single_and_composite_objectives() -> None:
    decision_input = _decision_input()
    evaluations, composite_score = ObjectiveRegistry().evaluate(decision_input)

    assert len(evaluations) == 2
    assert evaluations[0].name == "HVAC Energy"
    assert evaluations[0].satisfied is False
    assert evaluations[0].required_improvement == pytest.approx(60.0)
    assert evaluations[0].score.value > 70.0
    assert composite_score.value > 70.0
    assert len(composite_score.component_scores) == 2


def test_metric_resolvers_support_structured_and_generic_values() -> None:
    metrics = _metrics_with_values()

    assert resolve_metric_value(metrics, "hvac_energy_kwh") == pytest.approx(300.0)
    assert resolve_metric_unit(metrics, "hvac_energy_kwh") == "kWh"
    assert resolve_metric_value(metrics, "carbon_emissions_kgco2e") == pytest.approx(120.0)
    assert resolve_metric_unit(metrics, "carbon_emissions_kgco2e") == "kgCO2e"
    assert resolve_metric_value(metrics, "custom_goal_score") == pytest.approx(70.0)
    assert resolve_metric_unit(metrics, "custom_goal_score") == "score"
    assert resolve_metric_value(metrics, "missing_metric") is None
    assert resolve_metric_unit(metrics, "missing_metric") is None


def test_objective_registry_covers_maximize_balance_and_missing_metric_paths() -> None:
    goal = OptimizationGoal(
        summary="Improve ventilation while keeping a custom score balanced.",
        objectives=(
            OptimizationObjective(
                kind=OptimizationObjectiveKind.VENTILATION_EFFICIENCY,
                metric_name="ventilation_efficiency_percent",
                direction=OptimizationDirection.MAXIMIZE,
                target_reduction_percent=10.0,
                tolerance=0.01,
            ),
            OptimizationObjective(
                kind=OptimizationObjectiveKind.CUSTOM,
                metric_name="custom_goal_score",
                direction=OptimizationDirection.BALANCE,
                target_value=70.0,
                tolerance=0.0,
            ),
            OptimizationObjective(
                kind=OptimizationObjectiveKind.CUSTOM,
                metric_name="custom_goal_score",
                direction=OptimizationDirection.BALANCE,
            ),
            OptimizationObjective(
                kind=OptimizationObjectiveKind.CUSTOM,
                metric_name="missing_metric",
                direction=OptimizationDirection.BALANCE,
            ),
        ),
    )
    decision_input = _decision_input_for_goal(goal)
    evaluations, composite_score = ObjectiveRegistry().evaluate(decision_input)
    composite = ObjectiveRegistry().composite(goal)
    composite_evaluation = composite.evaluate(decision_input)

    ventilation, balanced, provisional, missing = evaluations

    assert ventilation.target_value == pytest.approx(90.2)
    assert ventilation.required_improvement == pytest.approx(8.2)
    assert ventilation.satisfied is False
    assert ventilation.score.value < 100.0
    assert balanced.satisfied is True
    assert balanced.score.value == pytest.approx(100.0)
    assert provisional.score.value == pytest.approx(50.0)
    assert provisional.target_value is None
    assert provisional.required_improvement is None
    assert "current baseline" in provisional.rationale
    assert missing.score.value == pytest.approx(0.0)
    assert missing.confidence == pytest.approx(0.0)
    assert missing.required_improvement is None
    assert "missing" in missing.rationale
    assert composite.name() == "Composite Objective"
    assert composite.priority() is ObjectivePriority.HIGH
    assert composite_score.component_scores
    assert set(composite.required_metrics()) == {
        "custom_goal_score",
        "missing_metric",
        "ventilation_efficiency_percent",
    }
    assert composite_evaluation.target_value == pytest.approx(100.0)
    assert composite_evaluation.required_improvement is not None


def test_constraint_evaluator_detects_current_violation_and_projected_risk() -> None:
    evaluator = ConstraintEvaluator()
    passing_input = _decision_input()
    failing_input = _decision_input(comfort_ppd=12.0)
    hypothesis = HypothesisEngine().generate(
        passing_input,
        ObjectiveRegistry().evaluate(passing_input)[0],
        focus_categories=(HypothesisCategory.HVAC,),
        limit=1,
    )[0]

    current_passing = evaluator.evaluate_current(passing_input)
    current_failing = evaluator.evaluate_current(failing_input)
    projected = evaluator.evaluate_hypothesis(passing_input, hypothesis)

    assert current_passing[0].status is ConstraintStatus.PASSED
    assert current_failing[0].status is ConstraintStatus.VIOLATED
    assert projected[0].status is ConstraintStatus.AT_RISK


def test_constraint_evaluator_supports_unverified_cost_carbon_and_generic_bounds() -> None:
    constraints = (
        OptimizationConstraint(target="missing_metric", maximum_value=1.0),
        OptimizationConstraint(
            target="operating_cost_usd",
            severity=ConstraintSeverity.SOFT,
            maximum_value=600.0,
        ),
        OptimizationConstraint(target="carbon_emissions_kgco2e", maximum_value=130.0),
        OptimizationConstraint(target="system_availability_percent", minimum_value=95.0),
    )
    decision_input = _decision_input_for_goal(
        _interpreted_goal().goal,
        constraints=constraints,
        metrics=_metrics_with_values(),
    )
    hypothesis = EngineeringHypothesis(
        title="Test mixed operational trade-off",
        summary="Exercise guardrails across cost, carbon, and generic bounds.",
        expected_energy_impact=ImpactEstimate(
            direction=ImpactDirection.DECREASE,
            magnitude=ImpactMagnitude.MEDIUM,
            summary="Availability pressure could accompany the change.",
        ),
        expected_cost_impact=ImpactEstimate(
            direction=ImpactDirection.INCREASE,
            magnitude=ImpactMagnitude.MEDIUM,
            summary="Operating cost could increase.",
        ),
        expected_carbon_impact=ImpactEstimate(
            direction=ImpactDirection.INCREASE,
            magnitude=ImpactMagnitude.MEDIUM,
            summary="Carbon emissions could increase.",
        ),
        confidence=0.6,
    )
    evaluator = ConstraintEvaluator()

    current = evaluator.evaluate_current(decision_input)
    projected = evaluator.evaluate_hypothesis(decision_input, hypothesis)

    assert current[0].status is ConstraintStatus.UNVERIFIED
    assert current[1].status is ConstraintStatus.PASSED
    assert current[2].status is ConstraintStatus.PASSED
    assert current[3].status is ConstraintStatus.PASSED
    assert projected[0].status is ConstraintStatus.UNVERIFIED
    assert projected[1].status is ConstraintStatus.AT_RISK
    assert projected[2].status is ConstraintStatus.AT_RISK
    assert projected[3].status is ConstraintStatus.AT_RISK


def test_hypothesis_engine_generates_targeted_candidates_and_empty_input_raises() -> None:
    engine = HypothesisEngine()
    decision_input = _decision_input()
    objective_evaluations = ObjectiveRegistry().evaluate(decision_input)[0]

    hypotheses = engine.generate(
        decision_input,
        objective_evaluations,
        focus_categories=(HypothesisCategory.HVAC, HypothesisCategory.CONTROLS),
    )

    assert hypotheses
    assert hypotheses[0].engineering_reason is not None
    assert all(item.confidence >= 0.35 for item in hypotheses)

    with pytest.raises(HypothesisGenerationError):
        engine.generate(decision_input, ())


def test_risk_assessor_escalates_for_comfort_and_hard_constraint_pressure() -> None:
    decision_input = _decision_input()
    objective_evaluations = ObjectiveRegistry().evaluate(decision_input)[0]
    hypothesis = HypothesisEngine().generate(
        decision_input,
        objective_evaluations,
        focus_categories=(HypothesisCategory.HVAC,),
        limit=1,
    )[0].model_copy(
        update={
            "confidence": 0.2,
            "expected_comfort_impact": ImpactEstimate(
                direction=ImpactDirection.DECREASE,
                magnitude=ImpactMagnitude.HIGH,
                summary="Comfort could degrade materially.",
            ),
            "expected_cost_impact": ImpactEstimate(
                direction=ImpactDirection.INCREASE,
                magnitude=ImpactMagnitude.MEDIUM,
                summary="Cost may temporarily increase.",
            ),
            "expected_carbon_impact": ImpactEstimate(
                direction=ImpactDirection.INCREASE,
                magnitude=ImpactMagnitude.MEDIUM,
                summary="Carbon could increase.",
            ),
            "estimated_risk": RiskLevel.HIGH,
        }
    )
    constraint_evaluations = ConstraintEvaluator().evaluate_hypothesis(decision_input, hypothesis)

    assessment = RiskAssessor().assess(
        hypothesis,
        constraint_evaluations=constraint_evaluations,
    )

    assert assessment.level is RiskLevel.CRITICAL
    assert assessment.mitigation_suggestions
    assert "comfort" in assessment.explanation.casefold()


@pytest.mark.parametrize("kind", tuple(OptimizationStrategyKind))
def test_strategy_registry_resolves_all_supported_strategies(
    kind: OptimizationStrategyKind,
) -> None:
    decision_input = _decision_input()
    planner = OptimizationPlanner()
    summary = planner.analyze(decision_input)
    strategy = StrategyRegistry(
        config=OptimizationConfig(
            reasoning=OptimizationReasoningSettings(random_seed=11)
        ),
        random_state=Random(11),
    ).resolve(kind)

    decision = strategy.decide(
        decision_input,
        summary.objective_evaluations,
        summary.hypothesis_evaluations,
    )

    assert decision.strategy_kind is kind
    assert decision.prioritized_hypothesis_ids


def test_planner_builds_decision_summary_and_satisfied_branch() -> None:
    decision_input = _decision_input()
    planner = OptimizationPlanner()
    summary = planner.analyze(decision_input)

    satisfied_goal = OptimizationGoal(
        summary="Maintain the current comfort condition.",
        objectives=(
            OptimizationObjective(
                kind=OptimizationObjectiveKind.THERMAL_COMFORT,
                metric_name="average_ppd_percent",
                target_value=8.0,
                tolerance=0.0,
            ),
        ),
    )
    satisfied_input = decision_input.model_copy(update={"goal": satisfied_goal, "constraints": ()})
    satisfied_summary = planner.analyze(satisfied_input)

    assert summary.hypothesis_evaluations
    assert summary.strategy_decision.selected_hypothesis_ids
    assert "remains open" in summary.summary
    assert "already satisfied" in satisfied_summary.summary


def test_planner_handles_carbon_cost_and_custom_objectives() -> None:
    goal = OptimizationGoal(
        summary="Reduce carbon and cost while preserving a custom score.",
        objectives=(
            OptimizationObjective(
                kind=OptimizationObjectiveKind.CARBON_EMISSIONS,
                metric_name="carbon_emissions_kgco2e",
                target_reduction_percent=10.0,
            ),
            OptimizationObjective(
                kind=OptimizationObjectiveKind.OPERATING_COST,
                metric_name="operating_cost_usd",
                target_reduction_percent=10.0,
            ),
            OptimizationObjective(
                kind=OptimizationObjectiveKind.CUSTOM,
                metric_name="custom_goal_score",
                direction=OptimizationDirection.BALANCE,
                target_value=70.0,
                tolerance=0.0,
            ),
        ),
    )
    decision_input = _decision_input_for_goal(goal, metrics=_metrics_with_values())
    summary = OptimizationPlanner().analyze(
        decision_input,
        strategy_kind=OptimizationStrategyKind.BALANCED,
    )

    assert len(summary.objective_evaluations) == 3
    assert summary.hypothesis_evaluations
    assert summary.strategy_decision.strategy_kind is OptimizationStrategyKind.BALANCED
    assert summary.next_focus_areas


class StubGoalInterpreter(GoalInterpreter):
    def __init__(self, interpretation: GoalInterpretation) -> None:
        super().__init__()
        self._interpretation = interpretation

    def interpret(self, goal_text: str) -> GoalInterpretation:
        del goal_text
        return self._interpretation


class StubPlanner(OptimizationPlanner):
    def __init__(self, summary: DecisionSummary) -> None:
        super().__init__()
        self._decision_summary = summary

    def analyze(
        self,
        decision_input: DecisionInput,
        *,
        strategy_kind: OptimizationStrategyKind | None = None,
    ) -> DecisionSummary:
        del decision_input, strategy_kind
        return self._decision_summary


class StubWorkflow(OptimizationWorkflow):
    def __init__(self, session: OptimizationSession) -> None:
        super().__init__(OptimizationConfig())
        self._session = session

    def start(self, request: OptimizationRequest) -> OptimizationSession:
        del request
        return self._session


def test_optimization_engine_supports_dependency_injection() -> None:
    interpretation = _interpreted_goal()
    decision_input = _decision_input()
    summary = OptimizationPlanner().analyze(decision_input)
    request = OptimizationRequest(
        goal=interpretation.goal,
        building_context=BuildingContext(building_name="HQ Tower"),
        constraints=interpretation.constraints,
    )
    session = OptimizationWorkflow(OptimizationConfig()).start(request)
    engine = OptimizationEngine(
        goal_interpreter=StubGoalInterpreter(interpretation),
        planner=StubPlanner(summary),
        workflow=StubWorkflow(session),
    )

    assert engine.interpret_goal("ignored") == interpretation
    assert engine.reason(decision_input) == summary
    assert engine.prepare(request) == session
