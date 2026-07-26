"""Immutable locator models for discovered EnergyPlus installations."""

from __future__ import annotations

import os
import sys
from enum import StrEnum
from hashlib import sha1
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

_IDD_FILENAME = "Energy+.idd"


class EnergyPlusCandidateSource(StrEnum):
    """Sources that may produce an EnergyPlus installation candidate."""

    EXPLICIT_CONFIGURED_EXECUTABLE = "explicit_configured_executable"
    ENERGYPLUS_HOME = "energyplus_home"
    CONFIGURED_INSTALLATION_ROOT = "configured_installation_root"
    STANDARD_DIRECTORY = "standard_directory"
    PATH = "path"


class EnergyPlusPlatform(StrEnum):
    """Supported operating-system families for EnergyPlus discovery."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


def detect_platform_name(platform_name: str | None = None) -> EnergyPlusPlatform:
    """Map a Python platform identifier to the locator platform enum."""
    normalized_name = (platform_name or sys.platform).lower()

    if normalized_name.startswith("win"):
        return EnergyPlusPlatform.WINDOWS

    if normalized_name.startswith("darwin"):
        return EnergyPlusPlatform.MACOS

    return EnergyPlusPlatform.LINUX


def expected_executable_name(platform: EnergyPlusPlatform) -> str:
    """Return the canonical EnergyPlus executable name for a platform."""
    if platform is EnergyPlusPlatform.WINDOWS:
        return "energyplus.exe"

    return "energyplus"


def normalize_candidate_path(path: Path) -> Path:
    """Normalize a candidate path without requiring the target to exist."""
    return Path(os.path.normpath(str(path.expanduser())))


def candidate_path_key(path: Path, platform: EnergyPlusPlatform) -> str:
    """Return a stable identity key for candidate deduplication."""
    normalized = normalize_candidate_path(path).as_posix()

    if platform is EnergyPlusPlatform.WINDOWS:
        return normalized.casefold()

    return normalized


def build_installation_id(path: Path, platform: EnergyPlusPlatform) -> str:
    """Create a deterministic installation identifier from the executable path."""
    digest = sha1(
        f"{platform.value}:{candidate_path_key(path, platform)}".encode(),
        usedforsecurity=False,
    ).hexdigest()
    return f"eplus-{platform.value}-{digest[:12]}"


class EnergyPlusInstallationCandidate(BaseModel):
    """Immutable description of a discovered EnergyPlus installation."""

    model_config = ConfigDict(frozen=True)

    installation_id: str = Field(min_length=1)
    source: EnergyPlusCandidateSource
    root_path: Path
    executable_path: Path
    idd_path: Path
    version: str | None = None
    platform: EnergyPlusPlatform
    supported: bool | None = None
    diagnostics: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        source: EnergyPlusCandidateSource,
        root_path: Path,
        executable_path: Path,
        platform: EnergyPlusPlatform,
        idd_path: Path | None = None,
        version: str | None = None,
        supported: bool | None = None,
        diagnostics: tuple[str, ...] = (),
    ) -> Self:
        """Build a candidate with normalized paths and a deterministic identifier."""
        normalized_root = normalize_candidate_path(root_path)
        normalized_executable = normalize_candidate_path(executable_path)
        normalized_idd = normalize_candidate_path(idd_path or normalized_root / _IDD_FILENAME)
        installation_id = build_installation_id(normalized_executable, platform)

        return cls(
            installation_id=installation_id,
            source=source,
            root_path=normalized_root,
            executable_path=normalized_executable,
            idd_path=normalized_idd,
            version=version,
            platform=platform,
            supported=supported,
            diagnostics=diagnostics,
        )

    def with_probe_result(
        self,
        *,
        version: str | None,
        supported: bool,
        diagnostics: tuple[str, ...],
    ) -> Self:
        """Return a copy enriched with version-probe or validation results."""
        return self.model_copy(
            update={
                "version": version,
                "supported": supported,
                "diagnostics": self.diagnostics + diagnostics,
            }
        )


__all__ = [
    "EnergyPlusCandidateSource",
    "EnergyPlusInstallationCandidate",
    "EnergyPlusPlatform",
    "build_installation_id",
    "candidate_path_key",
    "detect_platform_name",
    "expected_executable_name",
    "normalize_candidate_path",
]
