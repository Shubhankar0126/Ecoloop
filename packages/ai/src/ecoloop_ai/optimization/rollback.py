"""Rollback planning models for safe optimization execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class RollbackPlan(BaseModel):
    """A rollback outline that can be attached to a final optimization result."""

    model_config = ConfigDict(frozen=True)

    required: bool = False
    rationale: str | None = None
    steps: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_required_steps(self) -> RollbackPlan:
        """Require explicit steps when rollback has been marked as required."""
        if self.required and not self.steps:
            msg = "Rollback steps are required when rollback is enabled."
            raise ValueError(msg)

        return self


__all__ = ["RollbackPlan"]
