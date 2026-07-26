"""Simulation preflight validation for EnergyPlus input artifacts and options."""

from __future__ import annotations

import re
from pathlib import Path

from ecoloop_energyplus.config.models import SimulationSettings
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.validation.path_validator import PathValidator
from ecoloop_energyplus.infrastructure.validation.validation_result import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

_IDF_VERSION_PATTERN = re.compile(r"^\s*version\s*,", re.IGNORECASE)
_EPW_LOCATION_PREFIX = "location,"


class InputValidator:
    """Validate simulation input files and execution overrides before a run starts."""

    def __init__(
        self,
        *,
        path_validator: PathValidator | None = None,
        idf_scan_line_limit: int = 200,
    ) -> None:
        """Initialize the validator with reusable path validation and scan limits."""
        self._path_validator = path_validator or PathValidator()
        self._idf_scan_line_limit = idf_scan_line_limit

    def validate(self, spec: SimulationSpec, settings: SimulationSettings) -> ValidationResult:
        """Validate a simulation specification against filesystem and policy rules."""
        return ValidationResult.combine(
            self._validate_timeout(spec=spec, settings=settings),
            self._validate_parallel_jobs(spec=spec, settings=settings),
            self._validate_idf(spec.idf_path),
            self._validate_epw(spec.epw_path),
        )

    def _validate_timeout(
        self,
        *,
        spec: SimulationSpec,
        settings: SimulationSettings,
    ) -> ValidationResult:
        """Validate the effective simulation timeout override."""
        timeout_seconds = (
            spec.timeout_seconds
            if spec.timeout_seconds is not None
            else settings.default_timeout_seconds
        )

        if timeout_seconds <= 0:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.timeout.invalid",
                        message="Simulation timeout must be greater than zero seconds.",
                        target="simulation_spec.timeout_seconds",
                        recommendation=(
                            "Provide a positive timeout override or use the configured default."
                        ),
                    ),
                )
            )

        if timeout_seconds > settings.maximum_timeout_seconds:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.timeout.exceeds_maximum",
                        message=(
                            "Simulation timeout exceeds the configured maximum: "
                            f"{timeout_seconds} > {settings.maximum_timeout_seconds}."
                        ),
                        target="simulation_spec.timeout_seconds",
                        recommendation=(
                            "Lower the timeout override or raise the configured maximum."
                        ),
                    ),
                )
            )

        return ValidationResult.success()

    def _validate_parallel_jobs(
        self,
        *,
        spec: SimulationSpec,
        settings: SimulationSettings,
    ) -> ValidationResult:
        """Validate the effective parallel job override."""
        parallel_jobs = (
            spec.parallel_jobs
            if spec.parallel_jobs is not None
            else settings.default_parallel_jobs
        )

        if parallel_jobs <= 0:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.parallel_jobs.invalid",
                        message="Simulation parallel jobs must be greater than zero.",
                        target="simulation_spec.parallel_jobs",
                        recommendation=(
                            "Provide at least one parallel job or use the configured default."
                        ),
                    ),
                )
            )

        if parallel_jobs > settings.maximum_parallel_jobs:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.parallel_jobs.exceeds_maximum",
                        message=(
                            "Simulation parallel jobs exceed the configured maximum: "
                            f"{parallel_jobs} > {settings.maximum_parallel_jobs}."
                        ),
                        target="simulation_spec.parallel_jobs",
                        recommendation=(
                            "Lower the parallel job count or raise the configured maximum."
                        ),
                    ),
                )
            )

        return ValidationResult.success()

    def _validate_idf(self, path: Path) -> ValidationResult:
        """Validate IDF file existence, readability, size, and bounded version header."""
        file_result = self._validate_readable_non_empty_file(
            path=path,
            target="simulation_spec.idf_path",
            empty_code="simulation.idf.empty",
            empty_message=f"IDF file is empty: {path}.",
            empty_recommendation="Provide a non-empty EnergyPlus IDF file.",
        )
        if not file_result.valid:
            return file_result

        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if line_number > self._idf_scan_line_limit:
                        break

                    stripped_line = line.lstrip()
                    if stripped_line.startswith("!"):
                        continue

                    if _IDF_VERSION_PATTERN.match(stripped_line):
                        return ValidationResult.success()
        except OSError:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.idf.scan_failed",
                        message=f"IDF file could not be scanned: {path}.",
                        target="simulation_spec.idf_path",
                        recommendation=(
                            "Verify that the IDF file remains readable during validation."
                        ),
                    ),
                )
            )

        return ValidationResult.failure(
            issues=(
                self._error(
                    code="simulation.idf.missing_version_object",
                    message=(
                        "IDF file does not contain a Version object within the bounded scan "
                        f"limit of {self._idf_scan_line_limit} lines: {path}."
                    ),
                    target="simulation_spec.idf_path",
                    recommendation=(
                        "Add a Version object near the beginning of the IDF file or review "
                        "the file format."
                    ),
                ),
            )
        )

    def _validate_epw(self, path: Path) -> ValidationResult:
        """Validate EPW file existence, readability, size, and leading LOCATION header."""
        file_result = self._validate_readable_non_empty_file(
            path=path,
            target="simulation_spec.epw_path",
            empty_code="simulation.epw.empty",
            empty_message=f"EPW file is empty: {path}.",
            empty_recommendation="Provide a non-empty EnergyPlus weather file.",
        )
        if not file_result.valid:
            return file_result

        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
                header_line = handle.readline().strip()
        except OSError:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.epw.header_read_failed",
                        message=f"EPW header could not be read: {path}.",
                        target="simulation_spec.epw_path",
                        recommendation=(
                            "Verify that the EPW file remains readable during validation."
                        ),
                    ),
                )
            )

        if header_line.casefold().startswith(_EPW_LOCATION_PREFIX):
            return ValidationResult.success()

        return ValidationResult.failure(
            issues=(
                self._error(
                    code="simulation.epw.invalid_header",
                    message=f"EPW file does not begin with a LOCATION header: {path}.",
                    target="simulation_spec.epw_path",
                    recommendation="Provide a valid EnergyPlus EPW weather file.",
                ),
            )
        )

    def _validate_readable_non_empty_file(
        self,
        *,
        path: Path,
        target: str,
        empty_code: str,
        empty_message: str,
        empty_recommendation: str,
    ) -> ValidationResult:
        """Validate that an input file exists, is readable, and is non-empty."""
        file_result = self._path_validator.validate_file_exists(path, target=target)
        if not file_result.valid:
            return file_result

        readable_result = self._path_validator.validate_readable(path, target=target)
        if not readable_result.valid:
            return readable_result

        try:
            if path.stat().st_size <= 0:
                return ValidationResult.failure(
                    issues=(
                        self._error(
                            code=empty_code,
                            message=empty_message,
                            target=target,
                            recommendation=empty_recommendation,
                        ),
                    )
                )
        except OSError:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="simulation.input.stat_failed",
                        message=f"Input file metadata could not be read: {path}.",
                        target=target,
                        recommendation=(
                            "Verify that the input file remains accessible during validation."
                        ),
                    ),
                )
            )

        return ValidationResult.success()

    def _error(
        self,
        *,
        code: str,
        message: str,
        target: str,
        recommendation: str,
    ) -> ValidationIssue:
        """Create a standardized validation error issue."""
        return ValidationIssue(
            code=code,
            message=message,
            severity=ValidationSeverity.ERROR,
            target=target,
            recommendation=recommendation,
        )


__all__ = ["InputValidator"]
