from __future__ import annotations

from pathlib import Path

import pytest

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.csv import CsvParser


def test_csv_parser_extracts_columns_and_metrics(tmp_path: Path) -> None:
    path = tmp_path / "eplusout.csv"
    path.write_text(
        "\n".join(
            (
                "Date/Time,ZONE ONE:Zone Mean Air Temperature [C](Hourly),"
                "ZONE ONE:Zone Air Relative Humidity [%](Hourly),"
                "ZONE ONE:Fanger Model PMV(Hourly),"
                "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly),"
                "Whole Building:Electricity Consumption [kWh](Hourly)",
                "01/01  01:00:00,22,40,0.1,30,10",
                "01/01  02:00:00,24,50,0.3,32,20",
            )
        ),
        encoding="utf-8",
    )

    result = CsvParser().parse_file(path)

    assert result.source == path
    assert result.row_count == 2
    assert result.columns[0].name == "Date/Time"
    assert result.columns[1].key == "ZONE ONE"
    assert result.columns[1].unit == "C"
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(23.0)
    assert result.metrics.comfort.average_zone_humidity_percent == pytest.approx(45.0)
    assert result.metrics.comfort.average_pmv == pytest.approx(0.2)
    assert result.metrics.weather is not None
    assert result.metrics.weather.average_outdoor_dry_bulb_celsius == pytest.approx(31.0)
    assert result.metrics.energy is not None
    assert result.metrics.energy.electricity_consumption_kwh == pytest.approx(30.0)


def test_csv_parser_returns_empty_result_for_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    result = CsvParser().parse_file(path)

    assert result.row_count == 0
    assert result.columns == ()
    assert result.metrics.values == {}


def test_csv_parser_raises_output_parse_error_for_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"

    with pytest.raises(OutputParseError, match="CSV output could not be read"):
        CsvParser().parse_file(path)


def test_csv_parser_handles_sparse_rows_and_unstructured_headers(tmp_path: Path) -> None:
    path = tmp_path / "sparse.csv"
    path.write_text(
        "\n".join(
            (
                "Date/Time,Unused Value,ZONE ONE:Zone Mean Air Temperature [C](Hourly)",
                "01/01  01:00:00,,22",
                "01/01  02:00:00",
            )
        ),
        encoding="utf-8",
    )
    result = CsvParser().parse_file(path)

    assert result.row_count == 2
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(22.0)
