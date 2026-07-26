"""Subprocess-based EnergyPlus version detection."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_VERSION_PATTERN = re.compile(r"(?P<version>\d+(?:\.\d+)+)")


def parse_version_key(version: str | None) -> tuple[int, ...] | None:
    """Normalize a dotted version string into a comparable integer tuple."""
    if version is None or not version.strip():
        return None

    match = _VERSION_PATTERN.search(version)
    if match is None:
        return None

    parts = tuple(int(part) for part in match.group("version").split("."))
    trimmed_parts = parts
    while len(trimmed_parts) > 1 and trimmed_parts[-1] == 0:
        trimmed_parts = trimmed_parts[:-1]

    return trimmed_parts


class VersionProbeResult(BaseModel):
    """Outcome of executing the EnergyPlus version command."""

    model_config = ConfigDict(frozen=True)

    version: str | None = None
    supported: bool
    diagnostics: tuple[str, ...] = ()


class VersionProbe:
    """Resolve EnergyPlus versions by invoking the executable directly."""

    def __init__(self, *, timeout_seconds: int = 10) -> None:
        """Initialize the probe with a conservative command timeout."""
        self._timeout_seconds = timeout_seconds

    def probe(
        self,
        executable_path: Path,
        *,
        minimum_supported_version: str | None = None,
    ) -> VersionProbeResult:
        """Run ``energyplus --version`` and interpret the result."""
        command = [str(executable_path), "--version"]

        try:
            completed_process = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return VersionProbeResult(
                supported=False,
                diagnostics=(
                    f"EnergyPlus version command timed out after {self._timeout_seconds} seconds.",
                ),
            )
        except OSError as error:
            return VersionProbeResult(
                supported=False,
                diagnostics=(f"Failed to execute EnergyPlus version command: {error}.",),
            )

        combined_output = "\n".join(
            value.strip()
            for value in (completed_process.stdout, completed_process.stderr)
            if value and value.strip()
        )
        detected_version = self._extract_version(combined_output)
        diagnostics: list[str] = []

        if completed_process.returncode != 0:
            diagnostics.append(
                f"EnergyPlus version command returned exit code {completed_process.returncode}."
            )

        if detected_version is None:
            diagnostics.append("EnergyPlus version output did not include a parseable version.")

        minimum_key = (
            parse_version_key(minimum_supported_version) if minimum_supported_version else None
        )
        detected_key = parse_version_key(detected_version) if detected_version is not None else None
        if (
            detected_version is not None
            and minimum_key is not None
            and detected_key is not None
            and detected_key < minimum_key
        ):
            diagnostics.append(
                "EnergyPlus version "
                f"{detected_version} is below the minimum supported version "
                f"{minimum_supported_version}."
            )

        supported = not diagnostics
        return VersionProbeResult(
            version=detected_version,
            supported=supported,
            diagnostics=tuple(diagnostics),
        )

    def _extract_version(self, output: str) -> str | None:
        """Extract the first dotted version string from command output."""
        match = _VERSION_PATTERN.search(output)
        if match is None:
            return None

        return match.group("version")


__all__ = ["VersionProbe", "VersionProbeResult", "parse_version_key"]
