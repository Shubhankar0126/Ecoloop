"""Summary output parsing for EnergyPlus tabular artifacts."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.common import MetricNormalizer, SummaryCell
from ecoloop_energyplus.parser.summary.models import SummaryParseResult


class _SummaryHtmlParser(HTMLParser):
    """Extract headings and table rows from a lightweight HTML summary document."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[tuple[str | None, list[list[str]]]] = []
        self._active_heading_tag: str | None = None
        self._current_heading_parts: list[str] = []
        self._latest_heading: str | None = None
        self._inside_table = False
        self._inside_cell = False
        self._current_table_rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in {"h1", "h2", "h3", "b", "caption"}:
            self._active_heading_tag = normalized_tag
            self._current_heading_parts = []
            return

        if normalized_tag == "table":
            self._inside_table = True
            self._current_table_rows = []
            return

        if normalized_tag == "tr" and self._inside_table:
            self._current_row = []
            return

        if normalized_tag in {"th", "td"} and self._inside_table:
            self._inside_cell = True
            self._current_cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag == self._active_heading_tag:
            heading = " ".join(part.strip() for part in self._current_heading_parts).strip()
            self._latest_heading = heading or self._latest_heading
            self._active_heading_tag = None
            self._current_heading_parts = []
            return

        if normalized_tag in {"th", "td"} and self._inside_table and self._inside_cell:
            cell_text = " ".join(part.strip() for part in self._current_cell_parts).strip()
            self._current_row.append(cell_text)
            self._inside_cell = False
            self._current_cell_parts = []
            return

        if normalized_tag == "tr" and self._inside_table and self._current_row:
            self._current_table_rows.append(self._current_row)
            self._current_row = []
            return

        if normalized_tag == "table" and self._inside_table:
            self.tables.append((self._latest_heading, list(self._current_table_rows)))
            self._inside_table = False
            self._current_table_rows = []

    def handle_data(self, data: str) -> None:
        if self._active_heading_tag is not None:
            self._current_heading_parts.append(data)

        if self._inside_cell:
            self._current_cell_parts.append(data)


class SummaryParser:
    """Parse EnergyPlus summary outputs into normalized domain tables and metrics."""

    def __init__(
        self,
        *,
        metric_normalizer: MetricNormalizer | None = None,
    ) -> None:
        """Initialize the parser with an injectable normalization dependency."""
        self._metric_normalizer = metric_normalizer or MetricNormalizer()

    def parse_file(self, path: Path) -> SummaryParseResult:
        """Parse one EnergyPlus summary artifact from disk."""
        try:
            contents = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError as error:
            raise OutputParseError(
                message=f"EnergyPlus summary output could not be read: {path}.",
                context={"path": str(path)},
            ) from error

        return self.parse_text(contents, source=path)

    def parse_text(
        self,
        text: str,
        *,
        source: Path | None = None,
    ) -> SummaryParseResult:
        """Parse EnergyPlus summary HTML text into reusable summary tables."""
        html_parser = _SummaryHtmlParser()
        html_parser.feed(text)

        summary_cells: list[SummaryCell] = []
        for table_index, (heading, rows) in enumerate(html_parser.tables, start=1):
            if len(rows) < 2:
                continue

            table_name = heading or f"Summary Table {table_index}"
            headers = rows[0]
            for row in rows[1:]:
                if not row:
                    continue

                row_name = row[0].strip() or "Value"
                for column_index, cell_value in enumerate(row[1:], start=1):
                    column_name = (
                        headers[column_index].strip()
                        if column_index < len(headers) and headers[column_index].strip()
                        else f"Column {column_index}"
                    )
                    summary_cells.append(
                        SummaryCell(
                            table_name=table_name,
                            row_name=row_name,
                            column_name=column_name,
                            value=self._metric_normalizer.coerce_scalar(cell_value),
                            source_artifact=source.name if source is not None else None,
                        )
                    )

        metrics = self._metric_normalizer.build_metrics(summary_cells=tuple(summary_cells))
        return SummaryParseResult(
            source=source,
            metrics=metrics,
            tables=self._metric_normalizer.build_summary_tables(tuple(summary_cells)),
        )


__all__ = ["SummaryParser"]
