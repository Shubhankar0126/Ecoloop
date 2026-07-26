"""Severity levels parsed from EnergyPlus ERR diagnostics."""

from __future__ import annotations

from enum import StrEnum


class ErrSeverity(StrEnum):
    """Normalized severities extracted from ``eplusout.err``."""

    FATAL = "fatal"
    SEVERE = "severe"
    WARNING = "warning"


__all__ = ["ErrSeverity"]
