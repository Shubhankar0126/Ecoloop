"""Filesystem validation primitives for EnergyPlus infrastructure services."""

from __future__ import annotations

import os
from pathlib import Path

from ecoloop_energyplus.infrastructure.validation.validation_result import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class PathValidator:
    """Perform framework-independent filesystem checks for files and directories."""

    def validate_file_exists(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a path to exist and point to a regular file."""
        resolved_target = target or str(path)

        if not path.exists():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.missing",
                        message=f"Path does not exist: {path}.",
                        target=resolved_target,
                        recommendation="Create the file or correct the configured path.",
                    ),
                )
            )

        if not path.is_file():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_file",
                        message=f"Path is not a file: {path}.",
                        target=resolved_target,
                        recommendation="Provide a path that points to a regular file.",
                    ),
                )
            )

        return ValidationResult.success()

    def validate_directory_exists(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a path to exist and point to a directory."""
        resolved_target = target or str(path)

        if not path.exists():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.missing",
                        message=f"Path does not exist: {path}.",
                        target=resolved_target,
                        recommendation="Create the directory or correct the configured path.",
                    ),
                )
            )

        if not path.is_dir():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_directory",
                        message=f"Path is not a directory: {path}.",
                        target=resolved_target,
                        recommendation="Provide a path that points to a directory.",
                    ),
                )
            )

        return ValidationResult.success()

    def validate_readable(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a path to exist and be readable by the current process."""
        return self._validate_access(
            path=path,
            mode=os.R_OK,
            code="path.not_readable",
            message=f"Path is not readable: {path}.",
            target=target,
            recommendation="Grant read access or move the file to a readable location.",
        )

    def validate_writable(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a path to exist and be writable by the current process."""
        return self._validate_access(
            path=path,
            mode=os.W_OK,
            code="path.not_writable",
            message=f"Path is not writable: {path}.",
            target=target,
            recommendation="Grant write access or choose a writable directory.",
        )

    def validate_creatable(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a missing path to have a writable existing parent directory."""
        resolved_target = target or str(path)

        if path.exists():
            return ValidationResult.success()

        nearest_parent = self._nearest_existing_parent(path)
        if nearest_parent is None:
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_creatable",
                        message=(
                            "Path cannot be created because no existing parent was found: "
                            f"{path}."
                        ),
                        target=resolved_target,
                        recommendation="Create the parent directories or choose a different path.",
                    ),
                )
            )

        if not nearest_parent.is_dir():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_creatable",
                        message=(
                            "Path cannot be created because the nearest existing parent is not "
                            f"a directory: {nearest_parent}."
                        ),
                        target=resolved_target,
                        recommendation=(
                            "Replace the blocking file with a directory or choose a different "
                            "path."
                        ),
                    ),
                )
            )

        if not os.access(nearest_parent, os.W_OK):
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_creatable",
                        message=(
                            "Path cannot be created because the nearest existing parent is not "
                            f"writable: {nearest_parent}."
                        ),
                        target=resolved_target,
                        recommendation=(
                            "Grant write access to the parent directory or choose a different "
                            "path."
                        ),
                    ),
                )
            )

        return ValidationResult.success()

    def validate_executable(
        self,
        path: Path,
        *,
        target: str | None = None,
    ) -> ValidationResult:
        """Require a file path to be executable by the current process."""
        resolved_target = target or str(path)
        file_result = self.validate_file_exists(path, target=resolved_target)
        if not file_result.valid:
            return file_result

        if not os.access(path, os.X_OK):
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.not_executable",
                        message=f"Path is not executable: {path}.",
                        target=resolved_target,
                        recommendation="Grant execute permission or provide an executable file.",
                    ),
                )
            )

        return ValidationResult.success()

    def _validate_access(
        self,
        *,
        path: Path,
        mode: int,
        code: str,
        message: str,
        target: str | None,
        recommendation: str,
    ) -> ValidationResult:
        """Validate generic filesystem access for an existing path."""
        resolved_target = target or str(path)

        if not path.exists():
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="path.missing",
                        message=f"Path does not exist: {path}.",
                        target=resolved_target,
                        recommendation="Create the path or correct the configured location.",
                    ),
                )
            )

        if not os.access(path, mode):
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code=code,
                        message=message,
                        target=resolved_target,
                        recommendation=recommendation,
                    ),
                )
            )

        return ValidationResult.success()

    def _nearest_existing_parent(self, path: Path) -> Path | None:
        """Return the nearest existing parent directory candidate for a path."""
        current_path = path.parent
        while current_path != current_path.parent:
            if current_path.exists():
                return current_path

            current_path = current_path.parent

        if current_path.exists():
            return current_path

        return None

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


__all__ = ["PathValidator"]
