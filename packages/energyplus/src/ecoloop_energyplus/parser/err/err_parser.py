"""Parser for normalized diagnostics extracted from ``eplusout.err`` files."""

from __future__ import annotations

import re
from pathlib import Path

from ecoloop_energyplus.domain.exceptions import OutputParseError
from ecoloop_energyplus.parser.err.diagnostics import ErrDiagnostic, ErrDiagnosticsReport
from ecoloop_energyplus.parser.err.severity import ErrSeverity

_ERR_PATTERN = re.compile(
    r"^\s*\*\*\s*(?P<severity>fatal|severe|warning)\s*\*\*\s*(?P<message>.*)$",
    re.IGNORECASE,
)


class ErrParser:
    """Parse EnergyPlus ERR files into normalized diagnostic models."""

    def parse_file(self, path: Path) -> ErrDiagnosticsReport:
        """Parse one ``eplusout.err`` file from disk."""
        try:
            contents = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError as error:
            raise OutputParseError(
                message=f"EnergyPlus ERR file could not be read: {path}.",
                context={"path": str(path)},
            ) from error

        return self.parse_text(contents, source=path)

    def parse_text(
        self,
        text: str,
        *,
        source: Path | None = None,
    ) -> ErrDiagnosticsReport:
        """Parse normalized diagnostics from ERR text content."""
        diagnostics: list[ErrDiagnostic] = []

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            match = _ERR_PATTERN.match(raw_line)
            if match is None:
                continue

            severity = ErrSeverity(match.group("severity").casefold())
            message = match.group("message").strip() or raw_line.strip()
            diagnostics.append(
                ErrDiagnostic(
                    severity=severity,
                    message=message,
                    line_number=line_number,
                    raw_line=raw_line,
                )
            )

        return ErrDiagnosticsReport.from_diagnostics(tuple(diagnostics), source=source)


__all__ = ["ErrParser"]
