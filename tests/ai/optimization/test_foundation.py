from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from ecoloop_ai.models import BuildingContext
from ecoloop_ai.optimization import (
    CandidateEvaluation,
    CandidateStatus,
    ConstraintSeverity,
    ConvergenceAssessment,
    ConvergenceReason,
    DecisionStage,
    EngineeringHypothesis,
    EvaluationStatus,
    ExplainabilityRecord,
    OptimizationCandidate,
    OptimizationConfig,
    OptimizationConfigurationError,
    OptimizationConstraint,
    OptimizationDirection,
    OptimizationEngine,
    OptimizationGoal,
    OptimizationMetricSnapshot,
    OptimizationMetricTrend,
    OptimizationObjective,
    OptimizationObjectiveKind,
    OptimizationObservabilitySettings,
    OptimizationOutcomeReport,
    OptimizationPlan,
    OptimizationPlanStep,
    OptimizationRecommendation,
    OptimizationRequest,
    OptimizationResult,
    OptimizationSession,
    OptimizationStateError,
    OptimizationStatus,
    OptimizationStrategyKind,
    OptimizationStrategyProfile,
    RecommendationPriority,
    RiskTolerance,
    RollbackPlan,
)
from ecoloop_ai.optimization.history import OptimizationHistoryEntry
from ecoloop_ai.optimization.workflow import OptimizationWorkflow
from ecoloop_energyplus import (
    EnergyMetrics,
    SimulationMetadata,
    SimulationMetrics,
    SimulationResult,
    SimulationSpec,
    SimulationStatus,
)


def _spec(tmp_path: Path) -> SimulationSpec:
    return SimulationSpec(
        idf_path=tmp_path / "building.idf",
        epw_path=tmp_path / "weather.epw",
        timeout_seconds=90,
        parallel_jobs=1,
    )


def _building_context(tmp_path: Path) -> BuildingContext:
    return BuildingContext(
        building_name="HQ Tower",
        available_simulations={"baseline": _spec(tmp_path)},
        current_simulation_key="baseline",
        notes=("Primary office tower.",),
    )


def _goal() -> OptimizationGoal:
    return OptimizationGoal(
        summary="Reduce annual energy consumption while preserving comfort.",
        objectives=(
            OptimizationObjective(
                kind=OptimizationObjectiveKind.TOTAL_SITE_ENERGY,
                metric_name="total_site_energy_kwh",
                direction=OptimizationDirection.MINIMIZE,
                target_value=850.0,
                unit="kWh",
            ),
        ),
        success_criteria=("Annual site energy must decrease from the baseline.",),
        business_constraints=("Comfort must remain within acceptable bounds.",),
    )


def _request(tmp_path: Path, *, max_iterations: int | None = None) -> OptimizationRequest:
    return OptimizationRequest(
        goal=_goal(),
        building_context=_building_context(tmp_path),
        constraints=(
            OptimizationConstraint(
                target="average_zone_temperature_celsius",
                severity=ConstraintSeverity.HARD,
                minimum_value=21.0,
                maximum_value=25.0,
                unit="C",
            ),
        ),
        preferred_strategy=OptimizationStrategyKind.COMFORT_FIRST,
        max_iterations=max_iterations,
        metadata={"portfolio": "north-america"},
    )


def _result(identifier: str) -> SimulationResult:
    return SimulationResult(
        simulation_id=UUID(identifier),
        final_status=SimulationStatus.SUCCEEDED,
        metrics=SimulationMetrics(
            energy=EnergyMetrics(
                total_site_energy_kwh=900.0,
                electricity_consumption_kwh=500.0,
            )
        ),
        diagnostics=("Simulation completed.",),
        metadata=SimulationMetadata(
            energyplus_version="25.1.0",
            command_line=("energyplus",),
            exit_code=0,
            duration_ms=500,
            started_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 26, 9, 1, tzinfo=UTC),
        ),
    )


def _candidate() -> OptimizationCandidate:
    return OptimizationCandidate(
        iteration_index=1,
        strategy_kind=OptimizationStrategyKind.COMFORT_FIRST,
        hypothesis=EngineeringHypothesis(
            title="Raise chilled water setpoint slightly.",
            summary="A higher chilled water setpoint may reduce cooling energy.",
            expected_benefits=("Cooling demand should decrease.",),
            potential_risks=("Some perimeter zones may warm slightly.",),
            affected_systems=("Chilled water loop",),
            confidence=0.65,
        ),
        status=CandidateStatus.SELECTED,
        metrics=(
            OptimizationMetricSnapshot(
                name="total_site_energy_kwh",
                baseline_value=950.0,
                candidate_value=900.0,
                target_value=850.0,
                unit="kWh",
                trend=OptimizationMetricTrend.IMPROVED,
            ),
        ),
        evaluation=CandidateEvaluation(
            status=EvaluationStatus.IMPROVED,
            summary="The candidate improves the primary energy metric.",
            score_delta=-50.0,
            findings=("Cooling energy moved in the expected direction.",),
        ),
        simulation_result=_result("00000000-0000-0000-0000-000000000301"),
        notes=("Candidate selected for detailed review.",),
    )


def _plan() -> OptimizationPlan:
    return OptimizationPlan(
        summary="Evaluate one comfort-preserving chilled water adjustment.",
        strategy_kind=OptimizationStrategyKind.COMFORT_FIRST,
        steps=(
            OptimizationPlanStep(
                title="Propose the candidate change.",
                summary="Capture the chilled water setpoint adjustment hypothesis.",
                success_signal="A candidate hypothesis is recorded.",
            ),
        ),
    )


def _report(candidate: OptimizationCandidate) -> OptimizationOutcomeReport:
    recommendation = OptimizationRecommendation(
        title="Adopt the chilled water setpoint adjustment.",
        summary="The candidate reduced total site energy while staying within guardrails.",
        priority=RecommendationPriority.HIGH,
        expected_impacts=("Lower cooling energy.",),
        implementation_notes=("Roll out gradually and monitor zone comfort.",),
    )
    return OptimizationOutcomeReport(
        executive_summary="The optimization foundation prepared a complete outcome record.",
        goal_achieved=True,
        iterations_used=1,
        best_candidate_id=str(candidate.candidate_id),
        key_findings=("Energy use decreased relative to baseline.",),
        recommendations=(recommendation,),
        next_actions=("Validate the same hypothesis in another season.",),
    )


def test_package_exports_support_configuration_and_domain_models(tmp_path: Path) -> None:
    config = OptimizationConfig()
    request = _request(tmp_path)
    profile = OptimizationStrategyProfile(
        kind=OptimizationStrategyKind.COMFORT_FIRST,
        title="Comfort First",
        summary="Favor comfort-preserving changes over aggressive savings.",
        risk_tolerance=RiskTolerance.LOW,
        preferred_focus_areas=("Cooling setpoints",),
    )
    explainability = ExplainabilityRecord(
        summary="The chosen strategy prioritizes comfort stability.",
        assumptions=("The building already has acceptable controls.",),
        tradeoffs=("Savings may be smaller than an aggressive strategy.",),
        supporting_evidence=("Baseline comfort complaints are low.",),
    )
    error = OptimizationConfigurationError(
        context={"configured_limit": config.iteration.max_iterations}
    )

    assert config.strategy is OptimizationStrategyKind.AI_GUIDED
    assert config.resolve_max_iterations(request.max_iterations) == config.iteration.max_iterations
    assert profile.risk_tolerance is RiskTolerance.LOW
    assert explainability.summary.startswith("The chosen strategy")
    assert error.as_dict()["error_code"] == "ecoloop.ai.optimization_configuration_error"


def test_constraints_and_rollback_enforce_invariants() -> None:
    valid_constraint = OptimizationConstraint(
        target="pmv",
        severity=ConstraintSeverity.SOFT,
        maximum_value=0.5,
    )

    assert valid_constraint.maximum_value == 0.5

    with pytest.raises(ValueError, match="At least one constraint bound"):
        OptimizationConstraint(target="ppd")

    with pytest.raises(ValueError, match="minimum constraint bound cannot exceed"):
        OptimizationConstraint(target="temperature", minimum_value=25.0, maximum_value=21.0)

    with pytest.raises(ValueError, match="Rollback steps are required"):
        RollbackPlan(required=True)


def test_metric_delta_and_session_result_conversion(tmp_path: Path) -> None:
    metric = OptimizationMetricSnapshot(
        name="electricity_consumption_kwh",
        baseline_value=500.0,
        candidate_value=470.0,
        unit="kWh",
        trend=OptimizationMetricTrend.IMPROVED,
    )
    candidate = _candidate()
    session = OptimizationSession(
        request=_request(tmp_path),
        active_strategy=OptimizationStrategyKind.COMFORT_FIRST,
        max_iterations=4,
        best_candidate=candidate,
        recommendations=_report(candidate).recommendations,
        final_report=_report(candidate),
        explainability=ExplainabilityRecord(summary="The candidate improved energy use."),
        rollback_plan=RollbackPlan(
            required=True,
            rationale="A staged rollback is available if comfort degrades.",
            steps=("Restore the previous chilled water setpoint.",),
        ),
    )
    result = OptimizationResult.from_session(session)

    assert metric.delta() == pytest.approx(-30.0)
    assert (
        OptimizationMetricSnapshot(name="cooling_energy_kwh", baseline_value=120.0).delta()
        is None
    )
    assert result.session_id == session.session_id
    assert result.best_candidate == candidate
    assert result.final_report == session.final_report


def test_workflow_prepares_plan_candidate_and_completion_state(tmp_path: Path) -> None:
    workflow = OptimizationWorkflow(OptimizationConfig())
    request = _request(tmp_path)
    candidate = _candidate()
    report = _report(candidate)
    explainability = ExplainabilityRecord(
        summary="The candidate outperformed the baseline on the primary metric."
    )
    rollback_plan = RollbackPlan(
        required=True,
        rationale="A safe reversion path exists if comfort drifts.",
        steps=("Restore the original chilled water setpoint.",),
    )

    prepared = workflow.start(request)
    planned = workflow.record_plan(prepared, _plan())
    with_candidate = workflow.record_candidate(planned, candidate)
    with_convergence = workflow.record_convergence(
        with_candidate,
        ConvergenceAssessment(
            converged=True,
            reason=ConvergenceReason.GOAL_ACHIEVED,
            summary="The selected candidate satisfies the current objective threshold.",
            improvement_delta=-50.0,
            threshold=0.5,
        ),
    )
    completed = workflow.complete(
        with_convergence,
        report,
        recommendations=report.recommendations,
        explainability=explainability,
        rollback_plan=rollback_plan,
    )

    assert prepared.status is OptimizationStatus.PREPARED
    assert prepared.current_stage is DecisionStage.SESSION_CREATED
    assert prepared.active_strategy is OptimizationStrategyKind.COMFORT_FIRST
    assert len(prepared.trace) == 1
    assert len(prepared.history) == 1
    assert planned.current_plan is not None
    assert planned.status is OptimizationStatus.RUNNING
    assert with_candidate.best_candidate == candidate
    assert with_candidate.iteration_count == 1
    assert with_convergence.status is OptimizationStatus.CONVERGED
    assert completed.status is OptimizationStatus.CONVERGED
    assert completed.final_report == report
    assert completed.explainability == explainability
    assert completed.rollback_plan == rollback_plan
    assert completed.recommendations == report.recommendations
    assert completed.trace[-1].stage is DecisionStage.SESSION_COMPLETED
    assert isinstance(completed.history[-1], OptimizationHistoryEntry)


def test_workflow_rejects_excess_iterations_and_terminal_transitions(tmp_path: Path) -> None:
    config = OptimizationConfig()
    workflow = OptimizationWorkflow(config)

    with pytest.raises(OptimizationConfigurationError, match="exceeds the configured"):
        workflow.start(_request(tmp_path, max_iterations=config.iteration.max_iterations + 1))

    failed = workflow.fail(workflow.start(_request(tmp_path)), "The session was cancelled.")

    with pytest.raises(OptimizationStateError, match="terminated optimization session"):
        workflow.record_plan(failed, _plan())


def test_engine_prepares_sessions_and_exposes_stage_order(tmp_path: Path) -> None:
    engine = OptimizationEngine(config=OptimizationConfig())

    session = engine.prepare(_request(tmp_path))

    assert engine.config.strategy is OptimizationStrategyKind.AI_GUIDED
    assert session.status is OptimizationStatus.PREPARED
    assert session.request.goal.summary.startswith("Reduce annual energy consumption")
    assert engine.workflow_stages() == (
        "session_created",
        "goal_interpreted",
        "plan_created",
        "hypothesis_recorded",
        "risk_reviewed",
        "candidate_recorded",
        "convergence_reviewed",
        "report_prepared",
        "session_completed",
    )


def test_workflow_supports_minimal_observability_and_non_converged_completion(
    tmp_path: Path,
) -> None:
    config = OptimizationConfig(
        observability=OptimizationObservabilitySettings(
            decision_trace=False,
            save_history=False,
            explainability=False,
        ),
    )
    workflow = OptimizationWorkflow(config)
    request = OptimizationRequest(
        goal=_goal(),
        building_context=_building_context(tmp_path),
        constraints=(),
        preferred_strategy=None,
        max_iterations=2,
    )
    candidate = _candidate().model_copy(update={"status": CandidateStatus.PROPOSED})

    prepared = workflow.start(request)
    planned = workflow.record_plan(prepared, _plan())
    with_candidate = workflow.record_candidate(planned, candidate)
    with_convergence = workflow.record_convergence(
        with_candidate,
        ConvergenceAssessment(
            converged=False,
            reason=ConvergenceReason.NOT_REACHED,
            summary="Another candidate iteration is still required.",
            improvement_delta=-10.0,
            threshold=0.5,
        ),
    )
    completed = workflow.complete(
        with_convergence,
        OptimizationOutcomeReport(
            executive_summary="The session completed without meeting the convergence target.",
            goal_achieved=False,
            iterations_used=1,
        ),
    )

    assert prepared.active_strategy is OptimizationStrategyKind.AI_GUIDED
    assert prepared.trace == ()
    assert prepared.history == ()
    assert with_candidate.best_candidate is None
    assert with_convergence.status is OptimizationStatus.RUNNING
    assert completed.status is OptimizationStatus.COMPLETED
    assert completed.trace == ()
    assert completed.history == ()
