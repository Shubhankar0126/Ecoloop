"""Timeout configuration helpers for EnergyPlus subprocess execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExecutionTimeout(BaseModel):
    """Execution timeout policy for one subprocess invocation."""

    model_config = ConfigDict(frozen=True)

    seconds: float = Field(gt=0)
    poll_interval_seconds: float = Field(default=0.2, gt=0)
    grace_period_seconds: float = Field(default=5.0, gt=0)


def remaining_seconds(
    *,
    started_monotonic: float,
    current_monotonic: float,
    timeout: ExecutionTimeout,
) -> float:
    """Return the remaining wall-clock budget before a timeout is reached."""
    elapsed_seconds = current_monotonic - started_monotonic
    return timeout.seconds - elapsed_seconds


def next_wait_seconds(
    *,
    started_monotonic: float,
    current_monotonic: float,
    timeout: ExecutionTimeout,
) -> float:
    """Return the next bounded wait interval for cooperative polling."""
    remaining = remaining_seconds(
        started_monotonic=started_monotonic,
        current_monotonic=current_monotonic,
        timeout=timeout,
    )
    if remaining <= 0:
        return 0.0

    return min(timeout.poll_interval_seconds, remaining)


__all__ = [
    "ExecutionTimeout",
    "next_wait_seconds",
    "remaining_seconds",
]
