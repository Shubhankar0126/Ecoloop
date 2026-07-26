"""Enumerations used by EnergyPlus domain models."""

from __future__ import annotations

from enum import StrEnum


class SimulationStatus(StrEnum):
    """Lifecycle states for an EnergyPlus simulation request."""

    PENDING = "pending"
    VALIDATING = "validating"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    PARSE_FAILED = "parse_failed"


class SimulationArtifactKind(StrEnum):
    """Logical artifact kinds produced by EnergyPlus simulations."""

    INPUT = "input"
    LOG = "log"
    DIAGNOSTIC = "diagnostic"
    TABULAR = "tabular"
    TIME_SERIES = "time_series"
    DATABASE = "database"
    METADATA = "metadata"
    OTHER = "other"
