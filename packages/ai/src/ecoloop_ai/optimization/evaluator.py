"""Evaluation models for candidate assessment results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvaluationStatus(StrEnum):
    """Normalized status values for candidate evaluation outcomes."""

    NOT_EVALUATED = "not_evaluated"
    IMPROVED = "improved"
    REGRESSED = "regressed"
    INCONCLUSIVE = "inconclusive"


class CandidateEvaluation(BaseModel):
    """A reusable summary of how one candidate performed against the goal."""

    model_config = ConfigDict(frozen=True)

    status: EvaluationStatus
    summary: str = Field(min_length=1)
    score_delta: float | None = None
    findings: tuple[str, ...] = ()


__all__ = ["CandidateEvaluation", "EvaluationStatus"]
