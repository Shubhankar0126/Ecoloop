"""SQLite output parsing for EnergyPlus simulation artifacts."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.common import MetricNormalizer, ParsedSeries, SummaryCell
from ecoloop_energyplus.parser.sql.models import SqlParseResult

_SUMMARY_QUERY = """
SELECT
    ReportName,
    TableName,
    RowName,
    ColumnName,
    Units,
    Value
FROM TabularDataWithStrings
"""
_REPORT_DATA_QUERY = """
SELECT
    dictionary.KeyValue,
    dictionary.Name,
    dictionary.Units,
    data.Value
FROM ReportDataDictionary AS dictionary
INNER JOIN ReportData AS data
    ON dictionary.ReportDataDictionaryIndex = data.ReportDataDictionaryIndex
"""


class SqlParser:
    """Parse EnergyPlus SQLite output files into normalized domain metrics."""

    def __init__(
        self,
        *,
        metric_normalizer: MetricNormalizer | None = None,
    ) -> None:
        """Initialize the parser with an injectable normalization dependency."""
        self._metric_normalizer = metric_normalizer or MetricNormalizer()

    def parse_file(self, path: Path) -> SqlParseResult:
        """Parse one EnergyPlus SQLite output file from disk."""
        try:
            with closing(sqlite3.connect(path)) as connection:
                summary_cells = self._load_summary_cells(connection, source=path)
                series = self._load_series(connection)
        except sqlite3.Error as error:
            raise OutputParseError(
                message=f"EnergyPlus SQLite output could not be parsed: {path}.",
                context={"path": str(path)},
            ) from error

        return SqlParseResult(
            source=path,
            metrics=self._metric_normalizer.build_metrics(
                series=series,
                summary_cells=summary_cells,
            ),
            summary_cell_count=len(summary_cells),
            time_series_row_count=sum(len(item.values) for item in series),
        )

    def _load_summary_cells(
        self,
        connection: sqlite3.Connection,
        *,
        source: Path,
    ) -> tuple[SummaryCell, ...]:
        """Load tabular summary cells when the SQLite artifact contains them."""
        if not self._table_exists(connection, "TabularDataWithStrings"):
            return ()

        rows = connection.execute(_SUMMARY_QUERY).fetchall()
        return tuple(
            SummaryCell(
                table_name=str(row[1]).strip() or "Summary",
                row_name=str(row[2]).strip() or "Value",
                column_name=str(row[3]).strip() or "Value",
                value=self._metric_normalizer.coerce_scalar(str(row[5])),
                unit=str(row[4]).strip() or None,
                report_name=str(row[0]).strip() or None,
                source_artifact=str(source.name),
            )
            for row in rows
        )

    def _load_series(self, connection: sqlite3.Connection) -> tuple[ParsedSeries, ...]:
        """Load time-series report data when the SQLite artifact contains it."""
        if not (
            self._table_exists(connection, "ReportDataDictionary")
            and self._table_exists(connection, "ReportData")
        ):
            return ()

        grouped_values: dict[tuple[str | None, str, str | None], list[float]] = {}
        for key_value, name, units, value in connection.execute(_REPORT_DATA_QUERY):
            numeric_value = self._coerce_float(value)
            if numeric_value is None:
                continue

            grouped_values.setdefault(
                (
                    str(key_value).strip() or None,
                    str(name).strip(),
                    str(units).strip() or None,
                ),
                [],
            ).append(numeric_value)

        return tuple(
            ParsedSeries(
                key=key_value,
                name=name,
                unit=units,
                values=tuple(values),
                source_table="ReportData",
                source_artifact="eplusout.sql",
            )
            for (key_value, name, units), values in grouped_values.items()
        )

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        """Check whether one SQLite table exists in the output artifact."""
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        """Convert one SQLite value to float when possible."""
        if isinstance(value, int | float):
            return float(value)

        try:
            return float(str(value).strip())
        except ValueError:
            return None


__all__ = ["SqlParser"]
