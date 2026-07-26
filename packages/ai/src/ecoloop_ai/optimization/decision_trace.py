"""Decision trace models for auditable optimization workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DecisionStage(StrEnum):
    """Named stages in the optimization workflow lifecycle."""

    SESSION_CREATED = "session_created"
    GOAL_INTERPRETED = "goal_interpreted"
    PLAN_CREATED = "plan_created"
    HYPOTHESIS_RECORDED = "hypothesis_recorded"
    RISK_REVIEWED = "risk_reviewed"
    CANDIDATE_RECORDED = "candidate_recorded"
    CONVERGENCE_REVIEWED = "convergence_reviewed"
    REPORT_PREPARED = "report_prepared"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


class DecisionTraceEntry(BaseModel):
    """One immutable audit record produced while the workflow evolves."""

    model_config = ConfigDict(frozen=True)

    stage: DecisionStage
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)


__all__ = ["DecisionStage", "DecisionTraceEntry"]
