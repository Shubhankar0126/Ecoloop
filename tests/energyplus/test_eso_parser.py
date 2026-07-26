from __future__ import annotations

from pathlib import Path

import pytest

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.eso import EsoParser


def test_eso_parser_extracts_series_and_metrics() -> None:
    contents = "\n".join(
        (
            "Program Version,EnergyPlus, Version 25.1.0",
            "1,2,Environment,Site Outdoor Air Drybulb Temperature [C] !Hourly",
            "2,2,ZONE ONE,Zone Mean Air Temperature [C] !Hourly",
            "3,2,ZONE ONE,Zone Air Relative Humidity [%] !Hourly",
            "4,2,ZONE ONE,Fanger Model PMV !Hourly",
            "5,2,Whole Building,Electricity Consumption [kWh] !Hourly",
            "End of Data Dictionary",
            "1,30",
            "1,32",
            "2,22",
            "2,24",
            "3,40",
            "3,50",
            "4,0.1",
            "4,0.3",
            "5,10",
            "5,20",
            "End of Data",
        )
    )

    result = EsoParser().parse_text(contents)

    assert len(result.variables) == 5
    assert len(result.series) == 5
    assert result.metrics.comfort is not None
    assert result.metrics.comfort.average_zone_temperature_celsius == pytest.approx(23.0)
    assert result.metrics.comfort.average_zone_humidity_percent == pytest.approx(45.0)
    assert result.metrics.comfort.average_pmv == pytest.approx(0.2)
    assert result.metrics.weather is not None
    assert result.metrics.weather.average_outdoor_dry_bulb_celsius == pytest.approx(31.0)
    assert result.metrics.energy is not None
    assert result.metrics.energy.electricity_consumption_kwh == pytest.approx(30.0)


def test_eso_parser_ignores_unknown_records_and_non_numeric_values() -> None:
    contents = "\n".join(
        (
            "1,2,ZONE ONE,Zone Mean Air Temperature [C] !Hourly",
            "End of Data Dictionary",
            "unknown,row",
            "99,50",
            "1,22",
            "End of Data",
        )
    )

    result = EsoParser().parse_text(contents)

    assert len(result.series) == 1
    assert result.series[0].values == (22.0,)


def test_eso_parser_raises_output_parse_error_for_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.eso"

    with pytest.raises(OutputParseError, match="ESO output could not be read"):
        EsoParser().parse_file(path)


def test_eso_parser_private_helpers_cover_invalid_dictionary_and_data_lines() -> None:
    parser = EsoParser()

    assert parser._parse_definition("not-a-definition") is None
    assert parser._parse_definition("1") is None
    assert parser._parse_definition("bad,2,ZONE ONE,Temperature [C] !Hourly") is None
    assert parser._parse_data_line("1") == (None, ())
    assert parser._parse_data_line("bad,1.0") == (None, ())
    assert parser._split_name_and_unit("Plain Variable Name") == ("Plain Variable Name", None)
    assert parser._coerce_float("not-a-number") is None
