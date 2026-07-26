"""CSV output parsing for EnergyPlus simulation artifacts."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.common import MetricNormalizer, ParsedSeries
from ecoloop_energyplus.parser.csv.models import CsvColumn, CsvParseResult

_HEADER_PATTERN = re.compile(
    r"^(?:(?P<key>[^:]+):)?(?P<name>.+?)(?:\s*\[(?P<unit>[^\]]+)\])?(?:\((?P<frequency>[^)]+)\))?$"
)


class CsvParser:
    """Parse EnergyPlus CSV output into normalized typed metrics."""

    def __init__(
        self,
        *,
        metric_normalizer: MetricNormalizer | None = None,
    ) -> None:
        """Initialize the parser with an injectable normalization dependency."""
        self._metric_normalizer = metric_normalizer or MetricNormalizer()

    def parse_file(self, path: Path) -> CsvParseResult:
        """Parse one EnergyPlus CSV output artifact from disk."""
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                rows = list(reader)
        except OSError as error:
            raise OutputParseError(
                message=f"EnergyPlus CSV output could not be read: {path}.",
                context={"path": str(path)},
            ) from error
        except csv.Error as error:
            raise OutputParseError(
                message=f"EnergyPlus CSV output is malformed: {path}.",
                context={"path": str(path)},
            ) from error

        if not rows:
            return CsvParseResult.empty(source=path)

        columns = tuple(self._parse_column(header) for header in rows[0])
        series = self._build_series(columns, tuple(rows[1:]), source=path.name)
        return CsvParseResult(
            source=path,
            metrics=self._metric_normalizer.build_metrics(series=series),
            columns=columns,
            row_count=max(0, len(rows) - 1),
        )

    def _parse_column(self, header: str) -> CsvColumn:
        """Parse one EnergyPlus CSV header into a typed column definition."""
        normalized_header = header.strip()
        match = _HEADER_PATTERN.match(normalized_header)
        if match is None:
            return CsvColumn(raw_name=normalized_header, name=normalized_header)

        key = match.group("key")
        name = match.group("name").strip()
        unit = match.group("unit")
        frequency = match.group("frequency")
        return CsvColumn(
            raw_name=normalized_header,
            name=name,
            key=key.strip() if key else None,
            unit=unit.strip() if unit else None,
            frequency=frequency.strip() if frequency else None,
        )

    def _build_series(
        self,
        columns: tuple[CsvColumn, ...],
        rows: tuple[list[str], ...],
        *,
        source: str,
    ) -> tuple[ParsedSeries, ...]:
        """Build normalized numeric series from CSV rows and parsed columns."""
        series_values: list[list[float]] = [[] for _ in columns]

        for row in rows:
            for index, column in enumerate(columns):
                if index >= len(row):
                    continue

                numeric_value = self._coerce_float(row[index])
                if numeric_value is None:
                    continue

                if column.name.casefold() == "date/time":
                    continue

                series_values[index].append(numeric_value)

        return tuple(
            ParsedSeries(
                key=column.key,
                name=column.name,
                unit=column.unit,
                frequency=column.frequency,
                values=tuple(values),
                source_table="eplusout.csv",
                source_artifact=source,
            )
            for column, values in zip(columns, series_values, strict=True)
            if values
        )

    @staticmethod
    def _coerce_float(value: str) -> float | None:
        """Convert one CSV cell to float when possible."""
        normalized_value = value.strip()
        if not normalized_value:
            return None

        try:
            return float(normalized_value)
        except ValueError:
            return None


__all__ = ["CsvParser"]
