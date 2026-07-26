"""ESO output parsing for EnergyPlus simulation artifacts."""

from __future__ import annotations

import re
from pathlib import Path

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.common import MetricNormalizer, ParsedSeries
from ecoloop_energyplus.parser.eso.models import (
    EsoParseResult,
    EsoSeries,
    EsoVariableDefinition,
)

_UNIT_PATTERN = re.compile(r"^(?P<name>.+?)(?:\[(?P<unit>[^\]]+)\])?$")


class EsoParser:
    """Parse EnergyPlus ESO output into normalized time-series metrics."""

    def __init__(
        self,
        *,
        metric_normalizer: MetricNormalizer | None = None,
    ) -> None:
        """Initialize the parser with an injectable normalization dependency."""
        self._metric_normalizer = metric_normalizer or MetricNormalizer()

    def parse_file(self, path: Path) -> EsoParseResult:
        """Parse one EnergyPlus ESO output artifact from disk."""
        try:
            contents = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError as error:
            raise OutputParseError(
                message=f"EnergyPlus ESO output could not be read: {path}.",
                context={"path": str(path)},
            ) from error

        return self.parse_text(contents, source=path)

    def parse_text(
        self,
        text: str,
        *,
        source: Path | None = None,
    ) -> EsoParseResult:
        """Parse EnergyPlus ESO text content into typed series and metrics."""
        definitions: dict[int, EsoVariableDefinition] = {}
        values_by_record: dict[int, list[float]] = {}
        in_dictionary = True

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.casefold() == "end of data dictionary":
                in_dictionary = False
                continue

            if line.casefold().startswith("end of data"):
                break

            if in_dictionary:
                definition = self._parse_definition(line)
                if definition is not None:
                    definitions[definition.record_id] = definition
                continue

            record_id, numeric_values = self._parse_data_line(line)
            if record_id is None or record_id not in definitions:
                continue

            values_by_record.setdefault(record_id, []).extend(numeric_values)

        variables = tuple(definitions.values())
        series = tuple(
            EsoSeries(
                definition=definition,
                values=tuple(values_by_record.get(definition.record_id, ())),
            )
            for definition in variables
            if values_by_record.get(definition.record_id)
        )
        normalized_series = tuple(
            ParsedSeries(
                key=item.definition.key,
                name=item.definition.name,
                unit=item.definition.unit,
                frequency=item.definition.frequency,
                values=item.values,
                source_table="eplusout.eso",
                source_artifact=source.name if source is not None else "eplusout.eso",
            )
            for item in series
        )

        return EsoParseResult(
            source=source,
            metrics=self._metric_normalizer.build_metrics(series=normalized_series),
            variables=variables,
            series=series,
        )

    def _parse_definition(self, line: str) -> EsoVariableDefinition | None:
        """Parse one ESO data dictionary line into a typed variable definition."""
        if not line[:1].isdigit():
            return None

        metadata, _, frequency_part = line.partition("!")
        parts = [part.strip() for part in metadata.split(",") if part.strip()]
        if len(parts) < 2:
            return None

        try:
            record_id = int(parts[0])
        except ValueError:
            return None

        key = parts[-2] if len(parts) >= 3 else None
        name, unit = self._split_name_and_unit(parts[-1])
        frequency = frequency_part.strip() or None
        return EsoVariableDefinition(
            record_id=record_id,
            key=key,
            name=name,
            unit=unit,
            frequency=frequency,
        )

    def _parse_data_line(self, line: str) -> tuple[int | None, tuple[float, ...]]:
        """Parse one ESO data row into a record identifier and numeric values."""
        parts = [part.strip() for part in line.split(",") if part.strip()]
        if len(parts) < 2:
            return None, ()

        try:
            record_id = int(parts[0])
        except ValueError:
            return None, ()

        values = tuple(
            numeric_value
            for part in parts[1:]
            if (numeric_value := self._coerce_float(part)) is not None
        )
        return record_id, values

    def _split_name_and_unit(self, raw_name: str) -> tuple[str, str | None]:
        """Split a variable label into its name and optional bracketed unit."""
        match = _UNIT_PATTERN.match(raw_name.strip())
        if match is None:
            return raw_name.strip(), None

        name = match.group("name").strip()
        unit = match.group("unit")
        return name, unit.strip() if unit else None

    @staticmethod
    def _coerce_float(value: str) -> float | None:
        """Convert one ESO numeric token to float when possible."""
        try:
            return float(value)
        except ValueError:
            return None


__all__ = ["EsoParser"]
