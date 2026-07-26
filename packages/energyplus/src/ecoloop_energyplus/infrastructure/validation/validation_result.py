"""Immutable validation result models shared across EnergyPlus validators."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidationSeverity(StrEnum):
    """Supported severities for validation issues."""

    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    """A structured validation finding for configuration, inputs, or filesystem state."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: ValidationSeverity
    target: str = Field(min_length=1)
    recommendation: str | None = None


class ValidationResult(BaseModel):
    """Aggregated validation outcome with immutable issues and warnings."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        """Keep the result status aligned with the collected issue severities."""
        if any(issue.severity is not ValidationSeverity.ERROR for issue in self.issues):
            raise ValueError("issues must only contain error-severity validation issues.")

        if any(warning.severity is not ValidationSeverity.WARNING for warning in self.warnings):
            raise ValueError("warnings must only contain warning-severity validation issues.")

        expected_validity = not self.issues
        if self.valid is not expected_validity:
            raise ValueError("valid must be true when issues are empty and false otherwise.")

        return self

    @classmethod
    def success(
        cls,
        *,
        warnings: tuple[ValidationIssue, ...] = (),
    ) -> Self:
        """Build a successful result with optional warnings."""
        return cls(valid=True, issues=(), warnings=warnings)

    @classmethod
    def failure(
        cls,
        *,
        issues: tuple[ValidationIssue, ...],
        warnings: tuple[ValidationIssue, ...] = (),
    ) -> Self:
        """Build a failed result with one or more issues."""
        return cls(valid=False, issues=issues, warnings=warnings)

    @classmethod
    def from_issues(
        cls,
        *,
        issues: tuple[ValidationIssue, ...] = (),
        warnings: tuple[ValidationIssue, ...] = (),
    ) -> Self:
        """Build a result directly from issue collections."""
        return cls(valid=not issues, issues=issues, warnings=warnings)

    @classmethod
    def combine(cls, *results: ValidationResult) -> Self:
        """Merge multiple validation results into one aggregate outcome."""
        merged_issues = tuple(issue for result in results for issue in result.issues)
        merged_warnings = tuple(warning for result in results for warning in result.warnings)
        return cls.from_issues(issues=merged_issues, warnings=merged_warnings)


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
]
