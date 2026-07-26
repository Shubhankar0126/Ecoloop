"""Workflow state transitions for the optimization engine foundation."""

from __future__ import annotations

from datetime import UTC, datetime

from ecoloop_ai.optimization.config import OptimizationConfig
from ecoloop_ai.optimization.convergence import ConvergenceAssessment
from ecoloop_ai.optimization.decision_trace import DecisionStage, DecisionTraceEntry
from ecoloop_ai.optimization.exceptions import (
    OptimizationConfigurationError,
    OptimizationStateError,
)
from ecoloop_ai.optimization.explainability import ExplainabilityRecord
from ecoloop_ai.optimization.history import OptimizationHistoryEntry
from ecoloop_ai.optimization.models import (
    CandidateStatus,
    OptimizationCandidate,
    OptimizationRequest,
    OptimizationSession,
    OptimizationStatus,
)
from ecoloop_ai.optimization.planner import OptimizationPlan
from ecoloop_ai.optimization.recommendation import OptimizationRecommendation
from ecoloop_ai.optimization.report import OptimizationOutcomeReport
from ecoloop_ai.optimization.rollback import RollbackPlan


class OptimizationWorkflow:
    """Immutable state transition helper for optimization session lifecycles."""

    _workflow_stages: tuple[DecisionStage, ...] = (
        DecisionStage.SESSION_CREATED,
        DecisionStage.GOAL_INTERPRETED,
        DecisionStage.PLAN_CREATED,
        DecisionStage.HYPOTHESIS_RECORDED,
        DecisionStage.RISK_REVIEWED,
        DecisionStage.CANDIDATE_RECORDED,
        DecisionStage.CONVERGENCE_REVIEWED,
        DecisionStage.REPORT_PREPARED,
        DecisionStage.SESSION_COMPLETED,
    )
    _terminal_statuses: frozenset[OptimizationStatus] = frozenset(
        {
            OptimizationStatus.COMPLETED,
            OptimizationStatus.FAILED,
            OptimizationStatus.CANCELLED,
        }
    )
    _terminal_stages: frozenset[DecisionStage] = frozenset(
        {DecisionStage.SESSION_COMPLETED, DecisionStage.SESSION_FAILED}
    )

    def __init__(self, config: OptimizationConfig) -> None:
        """Initialize the workflow with resolved optimization configuration."""
        self._config = config

    @property
    def stages(self) -> tuple[DecisionStage, ...]:
        """Return the ordered workflow stages exposed by the foundation."""
        return self._workflow_stages

    def start(self, request: OptimizationRequest) -> OptimizationSession:
        """Create the initial immutable session state for one optimization request."""
        max_iterations = self._resolve_max_iterations(request.max_iterations)
        strategy = request.preferred_strategy or self._config.strategy
        trace: tuple[DecisionTraceEntry, ...] = ()
        history: tuple[OptimizationHistoryEntry, ...] = ()
        if self._config.observability.decision_trace:
            trace = (
                self._trace_entry(
                    stage=DecisionStage.SESSION_CREATED,
                    summary="Optimization session prepared.",
                    rationale="The request has been accepted and staged for execution.",
                    metadata={
                        "strategy": strategy.value,
                        "max_iterations": str(max_iterations),
                    },
                ),
            )
        if self._config.observability.save_history:
            history = (
                OptimizationHistoryEntry(
                    iteration_index=0,
                    stage=DecisionStage.SESSION_CREATED,
                    summary="Optimization session prepared.",
                ),
            )

        return OptimizationSession(
            request=request,
            status=OptimizationStatus.PREPARED,
            current_stage=DecisionStage.SESSION_CREATED,
            active_strategy=strategy,
            max_iterations=max_iterations,
            trace=trace,
            history=history,
        )

    def record_plan(
        self,
        session: OptimizationSession,
        plan: OptimizationPlan,
    ) -> OptimizationSession:
        """Attach a structured plan to the session and advance the workflow."""
        self._ensure_active(session)
        return self._update_session(
            session,
            current_stage=DecisionStage.PLAN_CREATED,
            status=OptimizationStatus.RUNNING,
            current_plan=plan,
            trace_entry=self._trace_entry(
                stage=DecisionStage.PLAN_CREATED,
                summary="Optimization plan recorded.",
                rationale="A structured plan is available for the next optimization iteration.",
                metadata={"strategy": plan.strategy_kind.value},
            ),
            history_entry=OptimizationHistoryEntry(
                iteration_index=session.iteration_count,
                stage=DecisionStage.PLAN_CREATED,
                summary=plan.summary,
            ),
        )

    def record_candidate(
        self,
        session: OptimizationSession,
        candidate: OptimizationCandidate,
    ) -> OptimizationSession:
        """Append one candidate to session history without executing it."""
        self._ensure_active(session)
        best_candidate = session.best_candidate
        if candidate.status is CandidateStatus.SELECTED:
            best_candidate = candidate

        return self._update_session(
            session,
            current_stage=DecisionStage.CANDIDATE_RECORDED,
            status=OptimizationStatus.RUNNING,
            iteration_count=max(session.iteration_count, candidate.iteration_index),
            best_candidate=best_candidate,
            candidates=(*session.candidates, candidate),
            trace_entry=self._trace_entry(
                stage=DecisionStage.CANDIDATE_RECORDED,
                summary="Optimization candidate recorded.",
                rationale="The workflow stored a structured candidate for later execution.",
                metadata={"candidate_id": str(candidate.candidate_id)},
            ),
            history_entry=OptimizationHistoryEntry(
                iteration_index=candidate.iteration_index,
                stage=DecisionStage.CANDIDATE_RECORDED,
                summary=candidate.hypothesis.title,
                candidate_id=str(candidate.candidate_id),
            ),
        )

    def record_convergence(
        self,
        session: OptimizationSession,
        assessment: ConvergenceAssessment,
    ) -> OptimizationSession:
        """Store a convergence decision and update session status when terminal."""
        self._ensure_active(session)
        status = OptimizationStatus.CONVERGED if assessment.converged else session.status
        return self._update_session(
            session,
            current_stage=DecisionStage.CONVERGENCE_REVIEWED,
            status=status,
            latest_convergence=assessment,
            trace_entry=self._trace_entry(
                stage=DecisionStage.CONVERGENCE_REVIEWED,
                summary="Convergence assessment recorded.",
                rationale=assessment.summary,
                metadata={"reason": assessment.reason.value},
            ),
            history_entry=OptimizationHistoryEntry(
                iteration_index=session.iteration_count,
                stage=DecisionStage.CONVERGENCE_REVIEWED,
                summary=assessment.summary,
            ),
        )

    def complete(
        self,
        session: OptimizationSession,
        report: OptimizationOutcomeReport,
        *,
        recommendations: tuple[OptimizationRecommendation, ...] = (),
        explainability: ExplainabilityRecord | None = None,
        rollback_plan: RollbackPlan | None = None,
    ) -> OptimizationSession:
        """Produce the terminal completed session state."""
        self._ensure_active(session)
        status = (
            OptimizationStatus.CONVERGED
            if session.latest_convergence is not None and session.latest_convergence.converged
            else OptimizationStatus.COMPLETED
        )
        return self._update_session(
            session,
            current_stage=DecisionStage.SESSION_COMPLETED,
            status=status,
            recommendations=recommendations or session.recommendations,
            final_report=report,
            explainability=explainability,
            rollback_plan=rollback_plan,
            trace_entry=self._trace_entry(
                stage=DecisionStage.SESSION_COMPLETED,
                summary="Optimization session completed.",
                rationale="A final report is available for downstream consumers.",
                metadata={"goal_achieved": str(report.goal_achieved)},
            ),
            history_entry=OptimizationHistoryEntry(
                iteration_index=session.iteration_count,
                stage=DecisionStage.SESSION_COMPLETED,
                summary=report.executive_summary,
                candidate_id=report.best_candidate_id,
            ),
        )

    def fail(self, session: OptimizationSession, reason: str) -> OptimizationSession:
        """Produce the terminal failed session state with a traceable reason."""
        self._ensure_active(session)
        return self._update_session(
            session,
            current_stage=DecisionStage.SESSION_FAILED,
            status=OptimizationStatus.FAILED,
            failure_reason=reason,
            trace_entry=self._trace_entry(
                stage=DecisionStage.SESSION_FAILED,
                summary="Optimization session failed.",
                rationale=reason,
            ),
            history_entry=OptimizationHistoryEntry(
                iteration_index=session.iteration_count,
                stage=DecisionStage.SESSION_FAILED,
                summary=reason,
            ),
        )

    def _resolve_max_iterations(self, requested_max_iterations: int | None) -> int:
        """Resolve one request's maximum iteration count against engine policy."""
        max_iterations = self._config.resolve_max_iterations(requested_max_iterations)
        if max_iterations > self._config.iteration.max_iterations:
            msg = "Requested max_iterations exceeds the configured optimization iteration limit."
            raise OptimizationConfigurationError(
                msg,
                context={
                    "requested_max_iterations": max_iterations,
                    "configured_limit": self._config.iteration.max_iterations,
                },
            )

        return max_iterations

    def _ensure_active(self, session: OptimizationSession) -> None:
        """Reject state transitions once the session has already terminated."""
        if (
            session.status in self._terminal_statuses
            or session.current_stage in self._terminal_stages
        ):
            msg = "Cannot transition a terminated optimization session."
            raise OptimizationStateError(
                msg,
                context={"status": session.status.value, "session_id": str(session.session_id)},
            )

    def _update_session(
        self,
        session: OptimizationSession,
        *,
        current_stage: DecisionStage,
        status: OptimizationStatus,
        current_plan: OptimizationPlan | None = None,
        best_candidate: OptimizationCandidate | None = None,
        candidates: tuple[OptimizationCandidate, ...] | None = None,
        recommendations: tuple[OptimizationRecommendation, ...] | None = None,
        latest_convergence: ConvergenceAssessment | None = None,
        final_report: OptimizationOutcomeReport | None = None,
        rollback_plan: RollbackPlan | None = None,
        explainability: ExplainabilityRecord | None = None,
        failure_reason: str | None = None,
        iteration_count: int | None = None,
        trace_entry: DecisionTraceEntry | None = None,
        history_entry: OptimizationHistoryEntry | None = None,
    ) -> OptimizationSession:
        """Create a new immutable session value with optional audit updates."""
        trace = session.trace
        if trace_entry is not None and self._config.observability.decision_trace:
            trace = (*trace, trace_entry)

        history = session.history
        if history_entry is not None and self._config.observability.save_history:
            history = (*history, history_entry)

        updates: dict[str, object] = {
            "current_stage": current_stage,
            "status": status,
            "trace": trace,
            "history": history,
            "updated_at": datetime.now(UTC),
        }
        if current_plan is not None:
            updates["current_plan"] = current_plan
        if best_candidate is not None:
            updates["best_candidate"] = best_candidate
        if candidates is not None:
            updates["candidates"] = candidates
        if recommendations is not None:
            updates["recommendations"] = recommendations
        if latest_convergence is not None:
            updates["latest_convergence"] = latest_convergence
        if final_report is not None:
            updates["final_report"] = final_report
        if rollback_plan is not None:
            updates["rollback_plan"] = rollback_plan
        if explainability is not None:
            updates["explainability"] = explainability
        if failure_reason is not None:
            updates["failure_reason"] = failure_reason
        if iteration_count is not None:
            updates["iteration_count"] = iteration_count

        return session.model_copy(update=updates)

    @staticmethod
    def _trace_entry(
        *,
        stage: DecisionStage,
        summary: str,
        rationale: str,
        metadata: dict[str, str] | None = None,
    ) -> DecisionTraceEntry:
        """Build one trace entry with consistent timestamp semantics."""
        return DecisionTraceEntry(
            stage=stage,
            summary=summary,
            rationale=rationale,
            metadata=metadata or {},
        )


__all__ = ["OptimizationWorkflow"]
