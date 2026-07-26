"""EnergyPlus command-line construction utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from ecoloop_energyplus.config.models import SimulationSettings
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.locator import EnergyPlusInstallationCandidate


class ExecutionCommand(BaseModel):
    """Immutable command specification for one subprocess invocation."""

    model_config = ConfigDict(frozen=True)

    command_line: tuple[str, ...]
    working_directory: Path
    environment_overrides: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def validate_command_line(self) -> Self:
        """Require a command line with at least one executable entry."""
        if not self.command_line:
            raise ValueError("ExecutionCommand requires a non-empty command line.")

        return self


class EnergyPlusCommandBuilder:
    """Build EnergyPlus CLI commands from validated package contracts."""

    def build(
        self,
        *,
        candidate: EnergyPlusInstallationCandidate,
        spec: SimulationSpec,
        settings: SimulationSettings,
        output_directory: Path,
        working_directory: Path | None = None,
        environment_overrides: dict[str, str] | None = None,
    ) -> ExecutionCommand:
        """Build an immutable EnergyPlus command specification."""
        command_line: list[str] = [
            str(candidate.executable_path),
            "-d",
            str(output_directory),
            "-w",
            str(spec.epw_path),
        ]

        if settings.force_annual:
            command_line.append("--annual")

        if settings.force_design_day:
            command_line.append("--design-day")

        if settings.run_readvars:
            command_line.append("--readvars")

        if settings.run_expandobjects:
            command_line.append("--expandobjects")

        command_line.append(str(spec.idf_path))
        normalized_environment = tuple(sorted((environment_overrides or {}).items()))

        return ExecutionCommand(
            command_line=tuple(command_line),
            working_directory=working_directory or output_directory,
            environment_overrides=normalized_environment,
        )


__all__ = [
    "EnergyPlusCommandBuilder",
    "ExecutionCommand",
]
