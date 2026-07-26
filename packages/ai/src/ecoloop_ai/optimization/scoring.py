"""Normalized score models and helpers for optimization reasoning."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ScoreDimension(StrEnum):
    """Supported scoring dimensions in the optimization reasoning layer."""

    ENERGY = "energy"
    COMFORT = "comfort"
    CARBON = "carbon"
    COST = "cost"
    PEAK_DEMAND = "peak_demand"
    COMPOSITE = "composite"
    GENERIC = "generic"


class NormalizedScore(BaseModel):
    """A score normalized onto a 0-100 scale where higher is better."""

    model_config = ConfigDict(frozen=True)

    dimension: ScoreDimension
    value: float = Field(ge=0, le=100)
    summary: str = Field(min_length=1)


class EnergyScore(NormalizedScore):
    """Normalized score for energy-oriented objectives."""

    dimension: ScoreDimension = ScoreDimension.ENERGY


class ComfortScore(NormalizedScore):
    """Normalized score for comfort-oriented objectives."""

    dimension: ScoreDimension = ScoreDimension.COMFORT


class CarbonScore(NormalizedScore):
    """Normalized score for carbon-oriented objectives."""

    dimension: ScoreDimension = ScoreDimension.CARBON


class CostScore(NormalizedScore):
    """Normalized score for cost-oriented objectives."""

    dimension: ScoreDimension = ScoreDimension.COST


class PeakDemandScore(NormalizedScore):
    """Normalized score for peak-demand-oriented objectives."""

    dimension: ScoreDimension = ScoreDimension.PEAK_DEMAND


class CompositeScore(NormalizedScore):
    """A weighted aggregate score composed from one or more component scores."""

    dimension: ScoreDimension = ScoreDimension.COMPOSITE
    component_scores: tuple[NormalizedScore, ...] = ()


def clamp_score(raw_value: float) -> float:
    """Clamp any floating-point score onto the inclusive 0-100 range."""
    return round(min(max(raw_value, 0.0), 100.0), 2)


def generic_score(value: float, summary: str) -> NormalizedScore:
    """Build a generic normalized score with clamped value semantics."""
    return NormalizedScore(
        dimension=ScoreDimension.GENERIC,
        value=clamp_score(value),
        summary=summary,
    )


def weighted_average(score_pairs: Sequence[tuple[NormalizedScore, float]]) -> float:
    """Compute a weighted score average while tolerating zero-weight inputs."""
    weighted_sum = 0.0
    total_weight = 0.0
    for score, weight in score_pairs:
        weighted_sum += score.value * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return clamp_score(weighted_sum / total_weight)


__all__ = [
    "CarbonScore",
    "ComfortScore",
    "CompositeScore",
    "CostScore",
    "EnergyScore",
    "NormalizedScore",
    "PeakDemandScore",
    "ScoreDimension",
    "clamp_score",
    "generic_score",
    "weighted_average",
]
