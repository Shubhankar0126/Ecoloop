"""High-level EnergyPlus execution orchestration built on the subprocess layer."""

from __future__ import annotations

from pathlib import Path
from threading import Event

from ecoloop_energyplus.config.models import SimulationSettings
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.execution.command_builder import (
    EnergyPlusCommandBuilder,
)
from ecoloop_energyplus.infrastructure.execution.execution_result import ExecutionResult
from ecoloop_energyplus.infrastructure.execution.process_manager import ProcessManager
from ecoloop_energyplus.infrastructure.execution.timeout import ExecutionTimeout
from ecoloop_energyplus.infrastructure.locator import EnergyPlusInstallationCandidate


class EnergyPlusRunner:
    """Compose command building and process execution for EnergyPlus runs."""

    def __init__(
        self,
        *,
        command_builder: EnergyPlusCommandBuilder | None = None,
        process_manager: ProcessManager | None = None,
    ) -> None:
        """Initialize the runner with injectable execution dependencies."""
        self._command_builder = command_builder or EnergyPlusCommandBuilder()
        self._process_manager = process_manager or ProcessManager()

    def run(
        self,
        *,
        candidate: EnergyPlusInstallationCandidate,
        spec: SimulationSpec,
        settings: SimulationSettings,
        output_directory: Path,
        working_directory: Path | None = None,
        cancellation_event: Event | None = None,
        environment_overrides: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute one EnergyPlus command using validated package contracts."""
        command = self._command_builder.build(
            candidate=candidate,
            spec=spec,
            settings=settings,
            output_directory=output_directory,
            working_directory=working_directory,
            environment_overrides=environment_overrides,
        )
        timeout = ExecutionTimeout(
            seconds=(
                spec.timeout_seconds
                if spec.timeout_seconds is not None
                else settings.default_timeout_seconds
            )
        )
        return self._process_manager.execute(
            command,
            timeout=timeout,
            cancellation_event=cancellation_event,
        )


__all__ = ["EnergyPlusRunner"]
