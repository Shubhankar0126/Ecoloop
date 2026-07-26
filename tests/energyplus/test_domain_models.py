from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ecoloop_energyplus.domain.enums import SimulationArtifactKind, SimulationStatus
from ecoloop_energyplus.domain.models import (
    ComfortMetrics,
    EnergyMetrics,
    HVACMetrics,
    Simulation,
    SimulationArtifact,
    SimulationMetadata,
    SimulationMetrics,
    SimulationMetricValue,
    SimulationResult,
    SimulationSpec,
    SummaryEntry,
    SummaryTable,
    WeatherMetrics,
    ZoneMetrics,
)


def test_simulation_status_enum_exposes_expected_terminal_state() -> None:
    assert SimulationStatus.SUCCEEDED.value == "succeeded"
    assert SimulationStatus.TIMED_OUT.value == "timed_out"


def test_simulation_metadata_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValidationError, match="Datetime values must be timezone-aware"):
        SimulationMetadata(started_at=datetime.now())


def test_simulation_metadata_allows_missing_optional_datetimes() -> None:
    metadata = SimulationMetadata()

    assert metadata.started_at is None
    assert metadata.completed_at is None


def test_simulation_metadata_preserves_explicit_none_optional_datetimes() -> None:
    metadata = SimulationMetadata(started_at=None, completed_at=None)

    assert metadata.started_at is None
    assert metadata.completed_at is None


def test_simulation_result_preserves_artifacts_and_metrics() -> None:
    simulation_id = uuid4()
    metadata = SimulationMetadata(
        energyplus_version="25.1.0",
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
    )
    artifact = SimulationArtifact(
        artifact_id="sql-output",
        kind=SimulationArtifactKind.DATABASE,
        relative_path=Path("raw/eplusout.sql"),
        media_type="application/vnd.sqlite3",
        size_bytes=4096,
    )
    metrics = SimulationMetrics(
        values={
            "site_energy_kwh": SimulationMetricValue(
                value=123.4,
                unit="kWh",
                source_artifact="sql-output",
                source_table="TabularDataWithStrings",
            )
        }
    )
    result = SimulationResult(
        simulation_id=simulation_id,
        final_status=SimulationStatus.SUCCEEDED,
        metrics=metrics,
        artifacts=(artifact,),
        diagnostics=("No severe errors reported.",),
        metadata=metadata,
    )

    assert result.simulation_id == simulation_id
    assert result.final_status is SimulationStatus.SUCCEEDED
    assert result.artifacts == (artifact,)
    assert result.metrics.values["site_energy_kwh"].unit == "kWh"


def test_simulation_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValidationError, match="Datetime values must be timezone-aware"):
        Simulation(
            simulation_id=uuid4(),
            status=SimulationStatus.PENDING,
            idf_path=Path("building.idf"),
            epw_path=Path("weather.epw"),
            created_at=datetime.now(),
        )


def test_simulation_spec_preserves_optional_runtime_overrides() -> None:
    spec = SimulationSpec(
        idf_path=Path("building.idf"),
        epw_path=Path("weather.epw"),
        timeout_seconds=1800,
        parallel_jobs=2,
    )

    assert spec.idf_path == Path("building.idf")
    assert spec.epw_path == Path("weather.epw")
    assert spec.timeout_seconds == 1800
    assert spec.parallel_jobs == 2


def test_simulation_metrics_supports_grouped_domain_metric_models() -> None:
    metrics = SimulationMetrics(
        values={
            "energy.total_site_energy_kwh": SimulationMetricValue(value=100.0, unit="kWh")
        },
        energy=EnergyMetrics(total_site_energy_kwh=100.0, electricity_consumption_kwh=60.0),
        hvac=HVACMetrics(
            heating_energy_kwh=20.0,
            cooling_energy_kwh=15.0,
            hvac_energy_kwh=40.0,
            equipment_loads_kwh=10.0,
        ),
        comfort=ComfortMetrics(
            average_zone_temperature_celsius=22.5,
            average_zone_humidity_percent=45.0,
            average_pmv=0.1,
            average_ppd_percent=8.0,
        ),
        weather=WeatherMetrics(
            average_outdoor_dry_bulb_celsius=30.0,
            average_outdoor_relative_humidity_percent=55.0,
        ),
        zones=(
            ZoneMetrics(
                zone_name="ZONE ONE",
                mean_air_temperature_celsius=22.0,
                mean_relative_humidity_percent=44.0,
            ),
        ),
        annual_summary=(
            SummaryTable(
                name="Annual Building Utility Performance Summary",
                entries=(
                    SummaryEntry(
                        row_name="Total Site Energy",
                        column_name="Annual Value",
                        value=100.0,
                        unit="kWh",
                    ),
                ),
            ),
        ),
    )

    assert metrics.energy is not None
    assert metrics.energy.total_site_energy_kwh == 100.0
    assert metrics.hvac is not None
    assert metrics.hvac.hvac_energy_kwh == 40.0
    assert metrics.comfort is not None
    assert metrics.comfort.average_zone_temperature_celsius == 22.5
    assert metrics.weather is not None
    assert metrics.weather.average_outdoor_dry_bulb_celsius == 30.0
    assert metrics.zones[0].zone_name == "ZONE ONE"
    assert metrics.annual_summary[0].entries[0].row_name == "Total Site Energy"
