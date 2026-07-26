"""Immutable models describing isolated EnergyPlus run directories."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


def _ensure_aware_datetime(value: datetime) -> datetime:
    """Require timezone-aware datetimes in run directory models."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must be timezone-aware.")

    return value


class RunDirectory(BaseModel):
    """Structured paths for one isolated simulation run directory."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    root_path: Path
    input_path: Path
    output_path: Path
    logs_path: Path
    metadata_path: Path
    stdout_path: Path
    stderr_path: Path
    manifest_path: Path
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        """Ensure the run-directory timestamp remains timezone-aware."""
        return _ensure_aware_datetime(value)


__all__ = ["RunDirectory"]
