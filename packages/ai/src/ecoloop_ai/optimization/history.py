"""History models for stored optimization iteration events."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from ecoloop_ai.optimization.decision_trace import DecisionStage


class OptimizationHistoryEntry(BaseModel):
    """A lightweight retained history event for one optimization iteration."""

    model_config = ConfigDict(frozen=True)

    iteration_index: int = Field(ge=0)
    stage: DecisionStage
    summary: str = Field(min_length=1)
    candidate_id: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = ["OptimizationHistoryEntry"]
