"""Immutable execution result models for EnergyPlus subprocess runs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ecoloop_energyplus.domain.enums import SimulationStatus

_TERMINAL_EXECUTION_STATUSES = {
    SimulationStatus.SUCCEEDED,
    SimulationStatus.FAILED,
    SimulationStatus.TIMED_OUT,
    SimulationStatus.CANCELLED,
}


def _ensure_aware_datetime(value: datetime) -> datetime:
    """Require timezone-aware datetimes in execution result models."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must be timezone-aware.")

    return value


class ExecutionResult(BaseModel):
    """Terminal result of one EnergyPlus-related subprocess execution."""

    model_config = ConfigDict(frozen=True)

    command_line: tuple[str, ...]
    working_directory: Path
    status: SimulationStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    diagnostics: tuple[str, ...] = ()
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)

    @field_validator("started_at", "completed_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        """Ensure execution timestamps remain timezone-aware."""
        return _ensure_aware_datetime(value)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        """Require execution results to carry a terminal simulation status."""
        if self.status not in _TERMINAL_EXECUTION_STATUSES:
            raise ValueError("ExecutionResult requires a terminal simulation status.")

        if not self.command_line:
            raise ValueError("ExecutionResult requires a non-empty command line.")

        return self


__all__ = ["ExecutionResult"]
