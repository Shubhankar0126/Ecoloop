from __future__ import annotations

import pytest

from ecoloop_energyplus.domain.models import ZoneMetrics
from ecoloop_energyplus.parser.common import MetricNormalizer, ParsedSeries, SummaryCell


def test_metric_normalizer_coerce_scalar_handles_supported_scalar_types() -> None:
    assert MetricNormalizer.coerce_scalar("true") is True
    assert MetricNormalizer.coerce_scalar("false") is False
    assert MetricNormalizer.coerce_scalar("42") == 42
    assert MetricNormalizer.coerce_scalar("4.25") == pytest.approx(4.25)
    assert MetricNormalizer.coerce_scalar("not-a-number") == "not-a-number"


def test_metric_normalizer_builds_metrics_from_summary_cells_and_series() -> None:
    normalizer = MetricNormalizer()
    summary_cells = (
        SummaryCell(
            table_name="Annual Building Utility Performance Summary",
            report_name="Annual Report",
            row_name="Total Site Energy",
            column_name="Annual Value",
            value=1.8,
            unit="GJ",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="End Uses",
            report_name="Annual Report",
            row_name="Electricity Consumption",
            column_name="Annual Value",
            value=1200.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="End Uses",
            report_name="Annual Report",
            row_name="Heating Energy",
            column_name="Annual Value",
            value=400.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="End Uses",
            report_name="Annual Report",
            row_name="Cooling Energy",
            column_name="Annual Value",
            value=300.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="End Uses",
            report_name="Annual Report",
            row_name="HVAC Energy",
            column_name="Annual Value",
            value=900.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="End Uses",
            report_name="Annual Report",
            row_name="Equipment Loads",
            column_name="Annual Value",
            value=250.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
        SummaryCell(
            table_name="Monthly Summary",
            report_name="Monthly Report",
            row_name="January",
            column_name="Electricity",
            value=100.0,
            unit="kWh",
            source_artifact="eplusout.sql",
        ),
    )
    series = (
        ParsedSeries(
            key="ZONE ONE",
            name="Zone Mean Air Temperature",
            unit="C",
            values=(22.0, 24.0),
            source_artifact="eplusout.csv",
        ),
        ParsedSeries(
            key="ZONE ONE",
            name="Zone Air Relative Humidity",
            unit="%",
            values=(40.0, 50.0),
            source_artifact="eplusout.csv",
        ),
        ParsedSeries(
            key="ZONE ONE",
            name="Fanger Model PMV",
            values=(0.1, 0.3),
            source_artifact="eplusout.csv",
        ),
        ParsedSeries(
            key="ZONE ONE",
            name="Fanger Model PPD",
            unit="%",
            values=(8.0, 10.0),
            source_artifact="eplusout.csv",
        ),
        ParsedSeries(
            key="Environment",
            name="Site Outdoor Air Drybulb Temperature",
            unit="C",
            values=(30.0, 32.0),
            source_artifact="eplusout.csv",
        ),
        ParsedSeries(
            key="Environment",
            name="Site Outdoor Air Relative Humidity",
            unit="%",
            values=(60.0, 50.0),
            source_artifact="eplusout.csv",
        ),
    )

    metrics = normalizer.build_metrics(series=series, summary_cells=summary_cells)

    assert metrics.energy is not None
    assert metrics.energy.total_site_energy_kwh == pytest.approx(500.0)
    assert metrics.energy.electricity_consumption_kwh == pytest.approx(1200.0)
    assert metrics.hvac is not None
    assert metrics.hvac.heating_energy_kwh == pytest.approx(400.0)
    assert metrics.hvac.cooling_energy_kwh == pytest.approx(300.0)
    assert metrics.hvac.hvac_energy_kwh == pytest.approx(900.0)
    assert metrics.hvac.equipment_loads_kwh == pytest.approx(250.0)
    assert metrics.comfort is not None
    assert metrics.comfort.average_zone_temperature_celsius == pytest.approx(23.0)
    assert metrics.comfort.average_zone_humidity_percent == pytest.approx(45.0)
    assert metrics.comfort.average_pmv == pytest.approx(0.2)
    assert metrics.comfort.average_ppd_percent == pytest.approx(9.0)
    assert metrics.weather is not None
    assert metrics.weather.average_outdoor_dry_bulb_celsius == pytest.approx(31.0)
    assert metrics.weather.average_outdoor_relative_humidity_percent == pytest.approx(55.0)
    assert metrics.zones[0].zone_name == "ZONE ONE"
    assert metrics.monthly_summary[0].name == "Monthly Summary"
    assert metrics.annual_summary[0].name == "Annual Building Utility Performance Summary"
    assert metrics.values["energy.total_site_energy_kwh"].value == pytest.approx(500.0)
    assert (
        metrics.values["zone.zone_one.mean_air_temperature_celsius"].value
        == pytest.approx(23.0)
    )


def test_metric_normalizer_build_summary_tables_groups_entries() -> None:
    normalizer = MetricNormalizer()
    summary_tables = normalizer.build_summary_tables(
        (
            SummaryCell(
                table_name="Annual Summary",
                report_name="Annual Report",
                row_name="Total Site Energy",
                column_name="Annual Value",
                value=100.0,
                unit="kWh",
            ),
            SummaryCell(
                table_name="Annual Summary",
                report_name="Annual Report",
                row_name="Electricity",
                column_name="Annual Value",
                value=60.0,
                unit="kWh",
            ),
        )
    )

    assert len(summary_tables) == 1
    assert summary_tables[0].report_name == "Annual Report"
    assert len(summary_tables[0].entries) == 2


def test_metric_normalizer_covers_private_helper_fallbacks() -> None:
    normalizer = MetricNormalizer()

    assert normalizer._build_comfort_metrics((ZoneMetrics(zone_name="ZONE TWO"),)) is None
    assert (
        normalizer._first_summary_metric(
            (
                SummaryCell(
                    table_name="Annual Summary",
                    row_name="Total Site Energy",
                    column_name="Annual Value",
                    value="not-a-number",
                    unit="kWh",
                ),
                SummaryCell(
                    table_name="Annual Summary",
                    row_name="Total Site Energy",
                    column_name="Annual Value",
                    value=100.0,
                    unit="mystery-unit",
                ),
            ),
            ("total site energy",),
            energy=True,
        )
        is None
    )
    assert (
        normalizer._sum_series_metric(
            (
                ParsedSeries(
                    name="Electricity Consumption",
                    unit="unknown",
                    values=(1.0, 2.0),
                ),
            ),
            ("electricity consumption",),
            energy=True,
        )
        is None
    )
    assert normalizer._series_zone_name(ParsedSeries(name="No Zone Name")) is None
    assert normalizer._series_zone_name(ParsedSeries(name=":invalid", key=" ")) is None
    assert normalizer._extract_key_from_name("No Colon Here") is None
    assert normalizer._as_float(True) == 1.0
    assert normalizer._as_float("bad-number") is None
    assert normalizer._energy_to_kwh(1.0, "mystery") is None
