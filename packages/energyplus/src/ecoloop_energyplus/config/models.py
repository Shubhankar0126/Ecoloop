"""Configuration models for the EnergyPlus platform package."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnergyPlusSettings(BaseModel):
    """Installation discovery and selection settings for EnergyPlus."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    validate_on_startup: bool = True
    preferred_version: str | None = None
    minimum_supported_version: str | None = None
    executable_path: Path | None = None
    installation_roots: tuple[Path, ...] = ()
    discover_on_path: bool = True
    allow_multiple_installations: bool = True


class SimulationSettings(BaseModel):
    """Execution policy settings shared by EnergyPlus simulation callers."""

    model_config = ConfigDict(frozen=True)

    default_timeout_seconds: int = Field(default=3600, ge=1)
    maximum_timeout_seconds: int = Field(default=21600, ge=1)
    default_parallel_jobs: int = Field(default=1, ge=1)
    maximum_parallel_jobs: int = Field(default=4, ge=1)
    run_readvars: bool = False
    run_expandobjects: bool = False
    force_annual: bool = False
    force_design_day: bool = False

    @model_validator(mode="after")
    def validate_ranges(self) -> SimulationSettings:
        """Ensure default execution limits do not exceed configured maximums."""
        if self.default_timeout_seconds > self.maximum_timeout_seconds:
            raise ValueError("default_timeout_seconds must not exceed maximum_timeout_seconds.")

        if self.default_parallel_jobs > self.maximum_parallel_jobs:
            raise ValueError("default_parallel_jobs must not exceed maximum_parallel_jobs.")

        return self


class OutputSettings(BaseModel):
    """Filesystem and retention settings for EnergyPlus run artifacts."""

    model_config = ConfigDict(frozen=True)

    root_directory: Path
    preserve_input_copies: bool = True
    keep_stdout_stderr: bool = True
    keep_raw_outputs: bool = True
    retention_success_days: int = Field(default=7, ge=0)
    retention_failure_days: int = Field(default=30, ge=0)
    cleanup_on_success: bool = False
    cleanup_on_failure: bool = False
    checksum_algorithm: str = "sha256"

    @model_validator(mode="after")
    def validate_root_directory(self) -> OutputSettings:
        """Require an absolute output root to keep run directories deterministic."""
        if not self.root_directory.is_absolute():
            raise ValueError("root_directory must be an absolute path.")

        return self


class EnergyPlusPlatformConfig(BaseModel):
    """Top-level configuration contract for the EnergyPlus platform package."""

    model_config = ConfigDict(frozen=True)

    energyplus: EnergyPlusSettings = Field(default_factory=EnergyPlusSettings)
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)
    output: OutputSettings
