from __future__ import annotations

from pathlib import Path

import pytest

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.summary import SummaryParser


def test_summary_parser_extracts_tables_and_metrics() -> None:
    contents = """
    <html>
      <body>
        <h2>Annual Building Utility Performance Summary</h2>
        <table>
          <tr><th>Row</th><th>Annual Value</th></tr>
          <tr><td>Total Site Energy</td><td>1200</td></tr>
        </table>
        <h2>Monthly Summary</h2>
        <table>
          <tr><th>Month</th><th>Electricity</th></tr>
          <tr><td>January</td><td>100</td></tr>
        </table>
      </body>
    </html>
    """

    result = SummaryParser().parse_text(contents)

    assert len(result.tables) == 2
    assert result.tables[0].name == "Annual Building Utility Performance Summary"
    assert result.tables[1].name == "Monthly Summary"
    assert result.metrics.energy is not None
    assert result.metrics.energy.total_site_energy_kwh == pytest.approx(1200.0)
    assert result.metrics.annual_summary[0].name == "Annual Building Utility Performance Summary"
    assert result.metrics.monthly_summary[0].name == "Monthly Summary"


def test_summary_parser_returns_empty_result_for_irrelevant_html() -> None:
    result = SummaryParser().parse_text("<html><body><p>No tables here.</p></body></html>")

    assert result.tables == ()
    assert result.metrics.values == {}


def test_summary_parser_raises_output_parse_error_for_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.htm"

    with pytest.raises(OutputParseError, match="summary output could not be read"):
        SummaryParser().parse_file(path)


def test_summary_parser_ignores_header_only_and_empty_rows() -> None:
    contents = """
    <html>
      <body>
        <h2>Header Only</h2>
        <table><tr><th>Only Header</th></tr></table>
        <h2>Sparse Table</h2>
        <table>
          <tr><th>Row</th><th>Value</th></tr>
          <tr></tr>
          <tr><td>Heating</td><td>50</td></tr>
        </table>
      </body>
    </html>
    """

    result = SummaryParser().parse_text(contents)

    assert len(result.tables) == 1
    assert result.tables[0].name == "Sparse Table"
