"""Final reporting models for optimization outcomes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.recommendation import OptimizationRecommendation


class OptimizationOutcomeReport(BaseModel):
    """A user-facing summary of the overall optimization outcome."""

    model_config = ConfigDict(frozen=True)

    executive_summary: str = Field(min_length=1)
    goal_achieved: bool
    iterations_used: int = Field(ge=0)
    best_candidate_id: str | None = None
    key_findings: tuple[str, ...] = ()
    recommendations: tuple[OptimizationRecommendation, ...] = ()
    next_actions: tuple[str, ...] = ()


__all__ = ["OptimizationOutcomeReport"]
