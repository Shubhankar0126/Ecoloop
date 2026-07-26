"""Filesystem-based EnergyPlus installation discovery."""

from __future__ import annotations

import glob
import os
from collections.abc import Iterable, Mapping
from pathlib import Path

from ecoloop_energyplus.config.models import EnergyPlusSettings
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
    detect_platform_name,
    expected_executable_name,
)


class FilesystemProbe:
    """Discover possible EnergyPlus installations from the local filesystem."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        platform_name: EnergyPlusPlatform | None = None,
        standard_search_patterns: Mapping[EnergyPlusPlatform, tuple[str, ...]] | None = None,
    ) -> None:
        """Initialize the probe with overridable environment and platform inputs."""
        self._environment = environment
        self._platform = platform_name or detect_platform_name()
        self._standard_search_patterns = (
            dict(standard_search_patterns) if standard_search_patterns is not None else None
        )

    def discover(self, settings: EnergyPlusSettings) -> tuple[EnergyPlusInstallationCandidate, ...]:
        """Discover potential installations without executing any version checks."""
        executable_name = expected_executable_name(self._platform)
        candidates: list[EnergyPlusInstallationCandidate] = []

        if settings.executable_path is not None:
            candidates.append(
                EnergyPlusInstallationCandidate.create(
                    source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
                    root_path=settings.executable_path.parent,
                    executable_path=settings.executable_path,
                    platform=self._platform,
                )
            )

        energyplus_home = self._environment_map().get("ENERGYPLUS_HOME", "").strip()
        if energyplus_home:
            home_root = Path(energyplus_home)
            candidates.append(
                EnergyPlusInstallationCandidate.create(
                    source=EnergyPlusCandidateSource.ENERGYPLUS_HOME,
                    root_path=home_root,
                    executable_path=home_root / executable_name,
                    platform=self._platform,
                )
            )

        for root_path in settings.installation_roots:
            candidates.append(
                EnergyPlusInstallationCandidate.create(
                    source=EnergyPlusCandidateSource.CONFIGURED_INSTALLATION_ROOT,
                    root_path=root_path,
                    executable_path=root_path / executable_name,
                    platform=self._platform,
                )
            )

        for root_path in self._iter_standard_roots():
            candidates.append(
                EnergyPlusInstallationCandidate.create(
                    source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
                    root_path=root_path,
                    executable_path=root_path / executable_name,
                    platform=self._platform,
                )
            )

        if settings.discover_on_path:
            for candidate in self._iter_path_candidates(executable_name=executable_name):
                candidates.append(candidate)

        return tuple(candidates)

    def _environment_map(self) -> Mapping[str, str]:
        """Return the environment mapping used for discovery."""
        if self._environment is not None:
            return self._environment

        return os.environ

    def _standard_patterns(self) -> tuple[str, ...]:
        """Return glob patterns for standard installation directories."""
        if self._standard_search_patterns is not None:
            return self._standard_search_patterns.get(self._platform, ())

        if self._platform is EnergyPlusPlatform.WINDOWS:
            return (r"C:\EnergyPlusV*",)

        if self._platform is EnergyPlusPlatform.MACOS:
            return ("/Applications/EnergyPlus-*",)

        return ("/usr/local/EnergyPlus-*", "/opt/EnergyPlus-*")

    def _iter_standard_roots(self) -> Iterable[Path]:
        """Yield installation roots matched from standard directory patterns."""
        for pattern in self._standard_patterns():
            for matched_path in sorted(glob.glob(pattern)):
                root_path = Path(matched_path)
                if root_path.is_dir():
                    yield root_path

    def _iter_path_candidates(
        self,
        *,
        executable_name: str,
    ) -> Iterable[EnergyPlusInstallationCandidate]:
        """Yield candidates found by scanning PATH directories for the executable."""
        raw_path = self._environment_map().get("PATH", "")
        if not raw_path:
            return

        for path_entry in raw_path.split(os.pathsep):
            normalized_entry = path_entry.strip()
            if not normalized_entry:
                continue

            executable_path = Path(normalized_entry) / executable_name
            if not executable_path.exists():
                continue

            yield EnergyPlusInstallationCandidate.create(
                source=EnergyPlusCandidateSource.PATH,
                root_path=executable_path.parent,
                executable_path=executable_path,
                platform=self._platform,
            )


__all__ = ["FilesystemProbe"]
