"""Composite EnergyPlus installation discovery and selection."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict

from ecoloop_energyplus.config.models import EnergyPlusSettings
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
    candidate_path_key,
)
from ecoloop_energyplus.infrastructure.locator.filesystem_probe import FilesystemProbe
from ecoloop_energyplus.infrastructure.locator.version_probe import VersionProbe, parse_version_key


class EnergyPlusLocatorResult(BaseModel):
    """Selection outcome for the composite EnergyPlus locator."""

    model_config = ConfigDict(frozen=True)

    selected_candidate: EnergyPlusInstallationCandidate | None = None
    all_candidates: tuple[EnergyPlusInstallationCandidate, ...] = ()
    selection_diagnostics: tuple[str, ...] = ()


class CompositeEnergyPlusLocator:
    """Discover, enrich, rank, and select EnergyPlus installations."""

    def __init__(
        self,
        *,
        filesystem_probe: FilesystemProbe | None = None,
        version_probe: VersionProbe | None = None,
    ) -> None:
        """Initialize the locator with injectable probe dependencies."""
        self._filesystem_probe = filesystem_probe or FilesystemProbe()
        self._version_probe = version_probe or VersionProbe()

    def locate(self, settings: EnergyPlusSettings) -> EnergyPlusLocatorResult:
        """Discover candidates and select the best supported installation."""
        discovered_candidates = self._filesystem_probe.discover(settings)
        unique_candidates, diagnostics = self._deduplicate_candidates(discovered_candidates)
        evaluated_candidates = tuple(
            self._evaluate_candidate(candidate, settings) for candidate in unique_candidates
        )
        ranked_candidates = tuple(
            sorted(
                evaluated_candidates,
                key=lambda candidate: self._ranking_key(
                    candidate=candidate,
                    preferred_version=settings.preferred_version,
                ),
                reverse=True,
            )
        )
        selected_candidate = next(
            (candidate for candidate in ranked_candidates if candidate.supported is True),
            None,
        )

        if selected_candidate is None:
            diagnostics.append("No supported EnergyPlus installation was found.")
        else:
            diagnostics.append(
                self._selection_reason(selected_candidate, settings.preferred_version)
            )

        return EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=ranked_candidates,
            selection_diagnostics=tuple(diagnostics),
        )

    def _deduplicate_candidates(
        self,
        candidates: tuple[EnergyPlusInstallationCandidate, ...],
    ) -> tuple[tuple[EnergyPlusInstallationCandidate, ...], list[str]]:
        """Deduplicate candidates by executable path while preserving discovery order."""
        unique_candidates: list[EnergyPlusInstallationCandidate] = []
        diagnostics: list[str] = []
        seen_paths: set[str] = set()

        for candidate in candidates:
            path_key = candidate_path_key(candidate.executable_path, candidate.platform)
            if path_key in seen_paths:
                diagnostics.append(
                    "Discarded duplicate EnergyPlus candidate for executable "
                    f"{candidate.executable_path}."
                )
                continue

            seen_paths.add(path_key)
            unique_candidates.append(candidate)

        return tuple(unique_candidates), diagnostics

    def _evaluate_candidate(
        self,
        candidate: EnergyPlusInstallationCandidate,
        settings: EnergyPlusSettings,
    ) -> EnergyPlusInstallationCandidate:
        """Validate a candidate executable and enrich it with version information."""
        validation_diagnostics = self._validate_executable(candidate)
        if validation_diagnostics:
            return candidate.with_probe_result(
                version=None,
                supported=False,
                diagnostics=validation_diagnostics,
            )

        probe_result = self._version_probe.probe(
            candidate.executable_path,
            minimum_supported_version=settings.minimum_supported_version,
        )
        return candidate.with_probe_result(
            version=probe_result.version,
            supported=probe_result.supported,
            diagnostics=probe_result.diagnostics,
        )

    def _validate_executable(
        self,
        candidate: EnergyPlusInstallationCandidate,
    ) -> tuple[str, ...]:
        """Perform lightweight executable validation without deeper input checks."""
        executable_path = candidate.executable_path
        diagnostics: list[str] = []

        if not executable_path.exists():
            diagnostics.append(f"Executable path does not exist: {executable_path}.")
            return tuple(diagnostics)

        if not executable_path.is_file():
            diagnostics.append(f"Executable path is not a file: {executable_path}.")
            return tuple(diagnostics)

        if candidate.platform is EnergyPlusPlatform.WINDOWS:
            if executable_path.suffix.casefold() != ".exe":
                diagnostics.append(
                    f"Executable path must end with .exe on Windows: {executable_path}."
                )
            return tuple(diagnostics)

        if not os.access(executable_path, os.X_OK):
            diagnostics.append(f"Executable path is not executable: {executable_path}.")

        return tuple(diagnostics)

    def _ranking_key(
        self,
        *,
        candidate: EnergyPlusInstallationCandidate,
        preferred_version: str | None,
    ) -> tuple[object, ...]:
        """Build a stable ranking key that follows the selection policy."""
        candidate_version_key = parse_version_key(candidate.version) or ()
        preferred_version_key = parse_version_key(preferred_version) if preferred_version else None
        preferred_match = (
            preferred_version_key is not None and candidate_version_key == preferred_version_key
        )
        source_priority = 0
        if candidate.source is EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE:
            source_priority = 3
        elif candidate.source in {
            EnergyPlusCandidateSource.ENERGYPLUS_HOME,
            EnergyPlusCandidateSource.CONFIGURED_INSTALLATION_ROOT,
            EnergyPlusCandidateSource.STANDARD_DIRECTORY,
        }:
            source_priority = 2
        elif candidate.source is EnergyPlusCandidateSource.PATH:
            source_priority = 1

        return (
            1 if candidate.supported is True else 0,
            (
                1
                if candidate.source is EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE
                else 0
            ),
            1 if preferred_match else 0,
            candidate_version_key,
            0 if candidate.source is EnergyPlusCandidateSource.PATH else 1,
            source_priority,
        )

    def _selection_reason(
        self,
        candidate: EnergyPlusInstallationCandidate,
        preferred_version: str | None,
    ) -> str:
        """Describe why a specific candidate was selected."""
        candidate_version_key = parse_version_key(candidate.version) or ()
        preferred_version_key = parse_version_key(preferred_version) if preferred_version else None

        if candidate.source is EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE:
            return (
                "Selected the explicitly configured EnergyPlus executable at "
                f"{candidate.executable_path}."
            )

        if preferred_version_key is not None and candidate_version_key == preferred_version_key:
            return (
                "Selected the EnergyPlus installation that matches the preferred version "
                f"{preferred_version}."
            )

        if candidate.source is EnergyPlusCandidateSource.PATH:
            return (
                "Selected the supported PATH-discovered EnergyPlus executable at "
                f"{candidate.executable_path}."
            )

        return (
            "Selected the highest supported EnergyPlus version at "
            f"{candidate.executable_path}."
        )


__all__ = ["CompositeEnergyPlusLocator", "EnergyPlusLocatorResult"]
