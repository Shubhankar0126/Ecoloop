"""Cleanup policies for isolated EnergyPlus run directories."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus.config.models import OutputSettings
from ecoloop_energyplus.domain.enums import SimulationStatus
from ecoloop_energyplus.infrastructure.output.run_directory import RunDirectory

_FAILURE_STATUSES = {
    SimulationStatus.CANCELLED,
    SimulationStatus.FAILED,
    SimulationStatus.PARSE_FAILED,
    SimulationStatus.TIMED_OUT,
}
_TERMINAL_STATUSES = _FAILURE_STATUSES | {SimulationStatus.SUCCEEDED}


class CleanupResult(BaseModel):
    """Immutable result of one run-directory cleanup decision."""

    model_config = ConfigDict(frozen=True)

    run_directory: Path
    removed: bool
    reason: str


class CleanupManager:
    """Apply retention and cleanup rules to EnergyPlus run directories."""

    def cleanup(
        self,
        run_directory: RunDirectory,
        *,
        status: SimulationStatus,
        settings: OutputSettings,
        completed_at: datetime | None = None,
        now: datetime | None = None,
        force: bool = False,
    ) -> CleanupResult:
        """Remove or retain a run directory according to configured policy."""
        reason = self._removal_reason(
            status=status,
            settings=settings,
            completed_at=completed_at,
            now=now,
            force=force,
        )
        if reason is None:
            return CleanupResult(
                run_directory=run_directory.root_path,
                removed=False,
                reason="Run directory is still within its configured retention policy.",
            )

        if not run_directory.root_path.exists():
            return CleanupResult(
                run_directory=run_directory.root_path,
                removed=False,
                reason="Run directory does not exist.",
            )

        shutil.rmtree(run_directory.root_path)
        return CleanupResult(
            run_directory=run_directory.root_path,
            removed=True,
            reason=reason,
        )

    def _removal_reason(
        self,
        *,
        status: SimulationStatus,
        settings: OutputSettings,
        completed_at: datetime | None,
        now: datetime | None,
        force: bool,
    ) -> str | None:
        """Return the reason a run directory should be removed, if any."""
        if force:
            return "Run directory cleanup was forced."

        if status not in _TERMINAL_STATUSES:
            return None

        if status is SimulationStatus.SUCCEEDED and settings.cleanup_on_success:
            return "Run directory was removed immediately after a successful run."

        if status in _FAILURE_STATUSES and settings.cleanup_on_failure:
            return "Run directory was removed immediately after a failed run."

        if completed_at is None:
            return None

        retention_days = (
            settings.retention_success_days
            if status is SimulationStatus.SUCCEEDED
            else settings.retention_failure_days
        )
        reference_time = now or datetime.now(tz=UTC)
        age_seconds = max(0.0, (reference_time - completed_at).total_seconds())
        if age_seconds >= retention_days * 86400:
            return "Run directory exceeded its configured retention period."

        return None


__all__ = [
    "CleanupManager",
    "CleanupResult",
]
