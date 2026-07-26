"""Core domain models for the EnergyPlus platform package."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ecoloop_energyplus.domain.enums import SimulationArtifactKind, SimulationStatus


def _ensure_aware_datetime(value: datetime) -> datetime:
    """Require timezone-aware datetimes in shared simulation models."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must be timezone-aware.")

    return value


class SimulationArtifact(BaseModel):
    """Metadata describing a stored EnergyPlus artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    kind: SimulationArtifactKind
    relative_path: Path
    media_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    checksum: str | None = None
    retention_class: str | None = None


class SimulationMetricValue(BaseModel):
    """A canonical metric value derived from EnergyPlus output artifacts."""

    model_config = ConfigDict(frozen=True)

    value: float | int | str | bool
    unit: str | None = None
    source_artifact: str | None = None
    source_table: str | None = None
    quality_flag: str | None = None


class EnergyMetrics(BaseModel):
    """Normalized building-level energy metrics in canonical units."""

    model_config = ConfigDict(frozen=True)

    total_site_energy_kwh: float | None = Field(default=None, ge=0)
    electricity_consumption_kwh: float | None = Field(default=None, ge=0)


class HVACMetrics(BaseModel):
    """Normalized HVAC and equipment energy metrics in canonical units."""

    model_config = ConfigDict(frozen=True)

    heating_energy_kwh: float | None = Field(default=None, ge=0)
    cooling_energy_kwh: float | None = Field(default=None, ge=0)
    hvac_energy_kwh: float | None = Field(default=None, ge=0)
    equipment_loads_kwh: float | None = Field(default=None, ge=0)


class ComfortMetrics(BaseModel):
    """Aggregated thermal comfort metrics normalized across building zones."""

    model_config = ConfigDict(frozen=True)

    average_zone_temperature_celsius: float | None = None
    average_zone_humidity_percent: float | None = Field(default=None, ge=0, le=100)
    average_pmv: float | None = None
    average_ppd_percent: float | None = Field(default=None, ge=0, le=100)


class WeatherMetrics(BaseModel):
    """Aggregated weather metrics derived from EnergyPlus output artifacts."""

    model_config = ConfigDict(frozen=True)

    average_outdoor_dry_bulb_celsius: float | None = None
    average_outdoor_relative_humidity_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class ZoneMetrics(BaseModel):
    """Normalized per-zone environmental and comfort metrics."""

    model_config = ConfigDict(frozen=True)

    zone_name: str = Field(min_length=1)
    mean_air_temperature_celsius: float | None = None
    mean_relative_humidity_percent: float | None = Field(default=None, ge=0, le=100)
    thermal_comfort_pmv: float | None = None
    thermal_comfort_ppd_percent: float | None = Field(default=None, ge=0, le=100)


class SummaryEntry(BaseModel):
    """One normalized cell from an EnergyPlus summary table."""

    model_config = ConfigDict(frozen=True)

    row_name: str = Field(min_length=1)
    column_name: str = Field(min_length=1)
    value: float | int | str | bool
    unit: str | None = None
    source_table: str | None = None
    source_artifact: str | None = None


class SummaryTable(BaseModel):
    """A normalized summary table extracted from EnergyPlus output artifacts."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    report_name: str | None = None
    entries: tuple[SummaryEntry, ...] = ()


class SimulationMetrics(BaseModel):
    """Named metrics extracted from one simulation execution."""

    model_config = ConfigDict(frozen=True)

    values: dict[str, SimulationMetricValue] = Field(default_factory=dict)
    energy: EnergyMetrics | None = None
    hvac: HVACMetrics | None = None
    comfort: ComfortMetrics | None = None
    weather: WeatherMetrics | None = None
    zones: tuple[ZoneMetrics, ...] = ()
    monthly_summary: tuple[SummaryTable, ...] = ()
    annual_summary: tuple[SummaryTable, ...] = ()


class SimulationMetadata(BaseModel):
    """Execution metadata captured for a simulation run."""

    model_config = ConfigDict(frozen=True)

    energyplus_version: str | None = None
    installation_root: Path | None = None
    command_line: tuple[str, ...] = ()
    exit_code: int | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    idf_checksum: str | None = None
    epw_checksum: str | None = None
    hostname: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def validate_optional_datetimes(cls, value: datetime | None) -> datetime | None:
        """Ensure optional execution timestamps remain timezone-aware."""
        if value is None:
            return None

        return _ensure_aware_datetime(value)


class SimulationResult(BaseModel):
    """Normalized result of a completed or terminated simulation execution."""

    model_config = ConfigDict(frozen=True)

    simulation_id: UUID
    final_status: SimulationStatus
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    artifacts: tuple[SimulationArtifact, ...] = ()
    diagnostics: tuple[str, ...] = ()
    metadata: SimulationMetadata


class SimulationSpec(BaseModel):
    """Framework-independent input contract for a planned simulation execution."""

    model_config = ConfigDict(frozen=True)

    idf_path: Path
    epw_path: Path
    timeout_seconds: int | None = None
    parallel_jobs: int | None = None


class Simulation(BaseModel):
    """A simulation request and its latest execution snapshot."""

    model_config = ConfigDict(frozen=True)

    simulation_id: UUID
    status: SimulationStatus
    idf_path: Path
    epw_path: Path
    created_at: datetime
    metadata: SimulationMetadata | None = None
    result: SimulationResult | None = None

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        """Ensure the simulation creation timestamp is timezone-aware."""
        return _ensure_aware_datetime(value)
