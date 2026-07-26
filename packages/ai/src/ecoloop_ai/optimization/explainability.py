"""Explainability models for optimization decisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExplainabilityRecord(BaseModel):
    """A normalized explanation of how the optimizer reached a conclusion."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1)
    assumptions: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()


__all__ = ["ExplainabilityRecord"]
