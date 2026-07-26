"""Convergence assessment models for optimization loops."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConvergenceReason(StrEnum):
    """Why the optimization loop stopped or can stop safely."""

    NOT_REACHED = "not_reached"
    GOAL_ACHIEVED = "goal_achieved"
    THRESHOLD_REACHED = "threshold_reached"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    NO_MATERIAL_CHANGE = "no_material_change"


class ConvergenceAssessment(BaseModel):
    """A typed convergence decision captured in workflow state."""

    model_config = ConfigDict(frozen=True)

    converged: bool
    reason: ConvergenceReason
    summary: str = Field(min_length=1)
    improvement_delta: float | None = None
    threshold: float | None = Field(default=None, ge=0)


__all__ = ["ConvergenceAssessment", "ConvergenceReason"]
