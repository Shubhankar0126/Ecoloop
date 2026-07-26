"""Startup readiness validation for the EnergyPlus platform."""

from __future__ import annotations

from pathlib import Path

from ecoloop_energyplus.config.models import EnergyPlusPlatformConfig
from ecoloop_energyplus.infrastructure.locator import (
    CompositeEnergyPlusLocator,
    EnergyPlusLocatorResult,
)
from ecoloop_energyplus.infrastructure.locator.version_probe import parse_version_key
from ecoloop_energyplus.infrastructure.validation.path_validator import PathValidator
from ecoloop_energyplus.infrastructure.validation.validation_result import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

_NO_SUPPORTED_INSTALLATION_MESSAGE = "No supported EnergyPlus installation was found."


class StartupValidator:
    """Validate configuration and host readiness before simulation workloads start."""

    def __init__(
        self,
        *,
        locator: CompositeEnergyPlusLocator | None = None,
        path_validator: PathValidator | None = None,
    ) -> None:
        """Initialize the validator with reusable locator and path-check dependencies."""
        self._locator = locator or CompositeEnergyPlusLocator()
        self._path_validator = path_validator or PathValidator()

    def validate(self, config: EnergyPlusPlatformConfig) -> ValidationResult:
        """Validate EnergyPlus startup readiness without launching a simulation."""
        if not config.energyplus.enabled:
            return ValidationResult.success(
                warnings=(
                    self._warning(
                        code="startup.energyplus.disabled",
                        message=(
                            "EnergyPlus startup validation was skipped because the platform "
                            "is disabled."
                        ),
                        target="config.energyplus.enabled",
                        recommendation=(
                            "Enable EnergyPlus before scheduling simulation workloads."
                        ),
                    ),
                )
            )

        configuration_result = self._validate_configuration(config)
        installation_result = self._validate_installation(
            locator_result=self._locator.locate(config.energyplus),
        )
        output_result = self._validate_output_root(config.output.root_directory)

        return ValidationResult.combine(
            configuration_result,
            installation_result,
            output_result,
        )

    def _validate_configuration(self, config: EnergyPlusPlatformConfig) -> ValidationResult:
        """Validate cross-field EnergyPlus configuration consistency."""
        issues: list[ValidationIssue] = []
        preferred_version = config.energyplus.preferred_version
        minimum_supported_version = config.energyplus.minimum_supported_version
        preferred_key = parse_version_key(preferred_version)
        minimum_key = parse_version_key(minimum_supported_version)

        if preferred_version is not None and preferred_key is None:
            issues.append(
                self._error(
                    code="startup.configuration.invalid_preferred_version",
                    message=f"Preferred EnergyPlus version is not parseable: {preferred_version}.",
                    target="config.energyplus.preferred_version",
                    recommendation="Use a dotted EnergyPlus version such as 25.1.0.",
                )
            )

        if minimum_supported_version is not None and minimum_key is None:
            issues.append(
                self._error(
                    code="startup.configuration.invalid_minimum_supported_version",
                    message=(
                        "Minimum supported EnergyPlus version is not parseable: "
                        f"{minimum_supported_version}."
                    ),
                    target="config.energyplus.minimum_supported_version",
                    recommendation="Use a dotted EnergyPlus version such as 23.1.0.",
                )
            )

        if preferred_key is not None and minimum_key is not None and preferred_key < minimum_key:
            issues.append(
                self._error(
                    code="startup.configuration.preferred_version_below_minimum",
                    message=(
                        "Preferred EnergyPlus version is below the configured minimum supported "
                        f"version: {preferred_version} < {minimum_supported_version}."
                    ),
                    target="config.energyplus.preferred_version",
                    recommendation=(
                        "Raise the preferred version or lower the minimum supported version."
                    ),
                )
            )

        return ValidationResult.from_issues(issues=tuple(issues))

    def _validate_installation(
        self,
        *,
        locator_result: EnergyPlusLocatorResult,
    ) -> ValidationResult:
        """Validate that at least one supported EnergyPlus installation is available."""
        selected_candidate = locator_result.selected_candidate
        if selected_candidate is None:
            warnings = tuple(
                self._warning(
                    code="startup.energyplus.locator_diagnostic",
                    message=diagnostic,
                    target="energyplus.installation",
                    recommendation=(
                        "Review the configured EnergyPlus paths, installation state, and "
                        "filesystem permissions."
                    ),
                )
                for diagnostic in locator_result.selection_diagnostics
                if diagnostic != _NO_SUPPORTED_INSTALLATION_MESSAGE
            )
            return ValidationResult.failure(
                issues=(
                    self._error(
                        code="startup.energyplus.installation_unavailable",
                        message="No supported EnergyPlus installation is available for startup.",
                        target="energyplus.installation",
                        recommendation=(
                            "Install a supported EnergyPlus version or correct the configured "
                            "executable path."
                        ),
                    ),
                ),
                warnings=warnings,
            )

        warnings = tuple(
            self._warning(
                code="startup.energyplus.candidate_discarded",
                message=diagnostic,
                target=str(candidate.executable_path),
                recommendation="Review discarded EnergyPlus candidates if they should be usable.",
            )
            for candidate in locator_result.all_candidates
            if candidate.supported is not True
            for diagnostic in candidate.diagnostics
        )
        return ValidationResult.success(warnings=warnings)

    def _validate_output_root(self, output_root: Path) -> ValidationResult:
        """Validate that the output root exists and is writable, or can be created."""
        target = "config.output.root_directory"
        directory_result = self._path_validator.validate_directory_exists(
            output_root,
            target=target,
        )
        if directory_result.valid:
            writable_result = self._path_validator.validate_writable(output_root, target=target)
            return ValidationResult.combine(directory_result, writable_result)

        if any(issue.code == "path.not_directory" for issue in directory_result.issues):
            return directory_result

        creatable_result = self._path_validator.validate_creatable(output_root, target=target)
        if creatable_result.valid:
            return ValidationResult.success(
                warnings=(
                    self._warning(
                        code="startup.output_root.creatable",
                        message=(
                            "Output root directory does not exist yet, but it can be created: "
                            f"{output_root}."
                        ),
                        target=target,
                        recommendation=(
                            "Create the directory before the first simulation run or allow the "
                            "runner to create it."
                        ),
                    ),
                )
            )

        return ValidationResult.combine(directory_result, creatable_result)

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

    def _warning(
        self,
        *,
        code: str,
        message: str,
        target: str,
        recommendation: str,
    ) -> ValidationIssue:
        """Create a standardized validation warning issue."""
        return ValidationIssue(
            code=code,
            message=message,
            severity=ValidationSeverity.WARNING,
            target=target,
            recommendation=recommendation,
        )


__all__ = ["StartupValidator"]
