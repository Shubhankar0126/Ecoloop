from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.sql import SqlParser


def _create_sqlite_output(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE TabularDataWithStrings (
                ReportName TEXT,
                TableName TEXT,
                RowName TEXT,
                ColumnName TEXT,
                Units TEXT,
                Value TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO TabularDataWithStrings VALUES (?, ?, ?, ?, ?, ?)",
            (
                (
                    "Annual Report",
                    "Annual Building Utility Performance Summary",
                    "Total Site Energy",
                    "Annual Value",
                    "GJ",
                    "1.8",
                ),
                (
                    "Annual Report",
                    "End Uses",
                    "Electricity Consumption",
                    "Annual Value",
                    "kWh",
                    "1200",
                ),
                (
                    "Annual Report",
                    "End Uses",
                    "Heating Energy",
                    "Annual Value",
                    "kWh",
                    "400",
                ),
                (
                    "Monthly Report",
                    "Monthly Summary",
                    "January",
                    "Electricity",
                    "kWh",
                    "100",
                ),
            ),
        )
        connection.execute(
            """
            CREATE TABLE ReportDataDictionary (
                ReportDataDictionaryIndex INTEGER PRIMARY KEY,
                KeyValue TEXT,
                Name TEXT,
                Units TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE ReportData (
                ReportDataDictionaryIndex INTEGER,
                Value REAL
            )
            """
        )
        connection.executemany(
            "INSERT INTO ReportDataDictionary VALUES (?, ?, ?, ?)",
            (
                (1, "ZONE ONE", "Zone Mean Air Temperature", "C"),
                (2, "ZONE ONE", "Zone Air Relative Humidity", "%"),
                (3, "Environment", "Site Outdoor Air Drybulb Temperature", "C"),
            ),
        )
        connection.executemany(
            "INSERT INTO ReportData VALUES (?, ?)",
            (
                (1, 22.0),
                (1, 24.0),
                (2, 40.0),
                (2, 50.0),
                (3, 30.0),
                (3, 32.0),
            ),
        )
        connection.commit()


def test_sql_parser_extracts_summary_and_timeseries_metrics(tmp_path: Path) -> None:
    path = tmp_path / "eplusout.sql"
    _create_sqlite_output(path)

    result = SqlParser().parse_file(path)

    assert result.source == path
    assert result.summary_cell_count == 4
    assert result.time_series_row_count == 6
    assert result.metrics.energy is not None
    assert result.metrics.energy.total_site_energy_kwh == pytest.approx(500.0)
    assert result.metrics.energy.electricity_consumption_kwh == pytest.approx(1200.0)
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(23.0)
    assert result.metrics.weather is not None
    assert result.metrics.weather.average_outdoor_dry_bulb_celsius == pytest.approx(31.0)
    assert result.metrics.monthly_summary[0].name == "Monthly Summary"
    assert result.metrics.annual_summary[0].name == "Annual Building Utility Performance Summary"


def test_sql_parser_returns_empty_metrics_when_optional_tables_are_absent(tmp_path: Path) -> None:
    path = tmp_path / "minimal.sql"
    with sqlite3.connect(path):
        pass

    result = SqlParser().parse_file(path)

    assert result.summary_cell_count == 0
    assert result.time_series_row_count == 0
    assert result.metrics.values == {}


def test_sql_parser_raises_output_parse_error_for_invalid_database(tmp_path: Path) -> None:
    path = tmp_path / "invalid.sql"
    path.write_text("not-a-sqlite-database", encoding="utf-8")

    with pytest.raises(OutputParseError, match="SQLite output could not be parsed"):
        SqlParser().parse_file(path)


def test_sql_parser_skips_non_numeric_report_data_values(tmp_path: Path) -> None:
    path = tmp_path / "mixed.sql"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE ReportDataDictionary (
                ReportDataDictionaryIndex INTEGER PRIMARY KEY,
                KeyValue TEXT,
                Name TEXT,
                Units TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE ReportData (
                ReportDataDictionaryIndex INTEGER,
                Value TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO ReportDataDictionary VALUES "
            "(1, 'ZONE ONE', 'Zone Mean Air Temperature', 'C')"
        )
        connection.executemany(
            "INSERT INTO ReportData VALUES (?, ?)",
            ((1, "invalid"), (1, "24")),
        )
        connection.commit()

    result = SqlParser().parse_file(path)

    assert result.time_series_row_count == 1
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(24.0)
