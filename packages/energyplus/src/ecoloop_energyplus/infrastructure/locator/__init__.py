"""Framework-independent EnergyPlus installation locator components."""

from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
)
from ecoloop_energyplus.infrastructure.locator.composite_locator import (
    CompositeEnergyPlusLocator,
    EnergyPlusLocatorResult,
)
from ecoloop_energyplus.infrastructure.locator.filesystem_probe import FilesystemProbe
from ecoloop_energyplus.infrastructure.locator.version_probe import VersionProbe, VersionProbeResult

__all__ = [
    "CompositeEnergyPlusLocator",
    "EnergyPlusCandidateSource",
    "EnergyPlusInstallationCandidate",
    "EnergyPlusLocatorResult",
    "EnergyPlusPlatform",
    "FilesystemProbe",
    "VersionProbe",
    "VersionProbeResult",
]
