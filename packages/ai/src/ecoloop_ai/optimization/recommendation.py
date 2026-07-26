"""Recommendation models produced by future optimization runs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RecommendationPriority(StrEnum):
    """Priority levels for optimization recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationRecommendation(BaseModel):
    """A reusable recommendation artifact prepared by the optimization workflow."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    expected_impacts: tuple[str, ...] = ()
    implementation_notes: tuple[str, ...] = ()


__all__ = ["OptimizationRecommendation", "RecommendationPriority"]
