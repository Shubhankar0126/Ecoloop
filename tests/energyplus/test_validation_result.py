from __future__ import annotations

import pytest
from pydantic import ValidationError

from ecoloop_energyplus.infrastructure.validation.validation_result import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


def _error_issue(code: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message="error",
        severity=ValidationSeverity.ERROR,
        target="target",
        recommendation="fix it",
    )


def _warning_issue(code: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message="warning",
        severity=ValidationSeverity.WARNING,
        target="target",
        recommendation="check it",
    )


def test_validation_result_combines_issues_and_warnings() -> None:
    warning = _warning_issue("validation.warning")
    failure = ValidationResult.failure(issues=(_error_issue("validation.error"),))
    success = ValidationResult.success(warnings=(warning,))

    combined = ValidationResult.combine(failure, success)

    assert combined.valid is False
    assert combined.issues[0].code == "validation.error"
    assert combined.warnings == (warning,)


def test_validation_result_rejects_inconsistent_state() -> None:
    with pytest.raises(ValidationError, match="valid must be true"):
        ValidationResult(valid=True, issues=(_error_issue("validation.error"),))

    with pytest.raises(ValidationError, match="issues must only contain"):
        ValidationResult(valid=False, issues=(_warning_issue("validation.warning"),))

    with pytest.raises(ValidationError, match="warnings must only contain"):
        ValidationResult(valid=True, warnings=(_error_issue("validation.error"),))
