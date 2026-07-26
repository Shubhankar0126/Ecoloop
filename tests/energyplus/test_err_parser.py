from __future__ import annotations

from pathlib import Path

import pytest

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.err import ErrParser, ErrSeverity


def test_err_parser_extracts_fatal_severe_and_warning_diagnostics() -> None:
    text = "\n".join(
        [
            "Program Version,EnergyPlus, Version 25.1.0",
            "** Warning ** Example warning",
            "Some unrelated line",
            "** Severe  ** Example severe diagnostic",
            "** Fatal ** Example fatal diagnostic",
        ]
    )

    report = ErrParser().parse_text(text)

    assert len(report.diagnostics) == 3
    assert report.warning_count == 1
    assert report.severe_count == 1
    assert report.fatal_count == 1
    assert report.diagnostics[0].severity is ErrSeverity.WARNING
    assert report.diagnostics[1].line_number == 4
    assert report.diagnostics[2].message == "Example fatal diagnostic"


def test_err_parser_parses_err_file_from_disk(tmp_path: Path) -> None:
    err_path = tmp_path / "eplusout.err"
    err_path.write_text("** Severe  ** Disk diagnostic\n", encoding="utf-8")

    report = ErrParser().parse_file(err_path)

    assert report.source == err_path
    assert report.severe_count == 1
    assert report.diagnostics[0].raw_line == "** Severe  ** Disk diagnostic"


def test_err_parser_returns_empty_report_for_text_without_diagnostics() -> None:
    report = ErrParser().parse_text("Program Version,EnergyPlus\nNo warnings.\n")

    assert report.diagnostics == ()
    assert report.fatal_count == 0
    assert report.severe_count == 0
    assert report.warning_count == 0


def test_err_parser_raises_output_parse_error_when_file_read_fails() -> None:
    with pytest.raises(OutputParseError, match="ERR file could not be read"):
        ErrParser().parse_file(Path("missing.err"))
