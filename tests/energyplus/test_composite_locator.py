from __future__ import annotations

import stat
from pathlib import Path

import pytest

from ecoloop_energyplus.config.models import EnergyPlusSettings
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
    detect_platform_name,
    expected_executable_name,
)
from ecoloop_energyplus.infrastructure.locator.composite_locator import CompositeEnergyPlusLocator
from ecoloop_energyplus.infrastructure.locator.filesystem_probe import FilesystemProbe
from ecoloop_energyplus.infrastructure.locator.version_probe import VersionProbe, VersionProbeResult

CURRENT_PLATFORM = detect_platform_name()


def _make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("energyplus", encoding="utf-8")
    if CURRENT_PLATFORM is not EnergyPlusPlatform.WINDOWS:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _make_non_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("energyplus", encoding="utf-8")
    if CURRENT_PLATFORM is not EnergyPlusPlatform.WINDOWS:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def _candidate(
    executable_path: Path,
    *,
    source: EnergyPlusCandidateSource,
) -> EnergyPlusInstallationCandidate:
    return EnergyPlusInstallationCandidate.create(
        source=source,
        root_path=executable_path.parent,
        executable_path=executable_path,
        platform=CURRENT_PLATFORM,
    )


class StubFilesystemProbe(FilesystemProbe):
    def __init__(self, candidates: tuple[EnergyPlusInstallationCandidate, ...]) -> None:
        self._candidates = candidates

    def discover(self, settings: EnergyPlusSettings) -> tuple[EnergyPlusInstallationCandidate, ...]:
        return self._candidates


class StubVersionProbe(VersionProbe):
    def __init__(self, results: dict[str, VersionProbeResult]) -> None:
        self.calls: list[tuple[Path, str | None]] = []
        self._results = results

    def probe(
        self,
        executable_path: Path,
        *,
        minimum_supported_version: str | None = None,
    ) -> VersionProbeResult:
        self.calls.append((executable_path, minimum_supported_version))
        return self._results[str(executable_path)]


def test_composite_locator_selects_a_single_supported_installation(tmp_path: Path) -> None:
    executable_path = _make_executable(
        tmp_path / "single" / expected_executable_name(CURRENT_PLATFORM)
    )
    candidate = _candidate(
        executable_path,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    version_probe = StubVersionProbe(
        {
            str(executable_path): VersionProbeResult(
                version="25.1.0",
                supported=True,
            )
        }
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=version_probe,
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is not None
    assert result.selected_candidate.executable_path == executable_path
    assert result.selected_candidate.version == "25.1.0"
    assert version_probe.calls == [(executable_path, None)]


def test_composite_locator_deduplicates_candidates_before_version_probe(tmp_path: Path) -> None:
    executable_path = _make_executable(
        tmp_path / "duplicate" / expected_executable_name(CURRENT_PLATFORM)
    )
    explicit_candidate = _candidate(
        executable_path,
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
    )
    path_candidate = _candidate(executable_path, source=EnergyPlusCandidateSource.PATH)
    version_probe = StubVersionProbe(
        {
            str(executable_path): VersionProbeResult(
                version="25.1.0",
                supported=True,
            )
        }
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((explicit_candidate, path_candidate)),
        version_probe=version_probe,
    )

    result = locator.locate(EnergyPlusSettings(executable_path=executable_path))

    assert len(result.all_candidates) == 1
    assert result.selected_candidate is not None
    assert (
        result.selected_candidate.source
        is EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE
    )
    assert len(version_probe.calls) == 1
    assert "Discarded duplicate EnergyPlus candidate" in result.selection_diagnostics[0]


def test_composite_locator_returns_no_selection_for_unsupported_versions(tmp_path: Path) -> None:
    executable_path = _make_executable(
        tmp_path / "unsupported" / expected_executable_name(CURRENT_PLATFORM)
    )
    candidate = _candidate(
        executable_path,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=StubVersionProbe(
            {
                str(executable_path): VersionProbeResult(
                    version="22.1.0",
                    supported=False,
                    diagnostics=("below minimum",),
                )
            }
        ),
    )

    result = locator.locate(EnergyPlusSettings(minimum_supported_version="23.1.0"))

    assert result.selected_candidate is None
    assert result.all_candidates[0].supported is False
    assert result.selection_diagnostics[-1] == "No supported EnergyPlus installation was found."


def test_composite_locator_reports_missing_executables_without_probing(tmp_path: Path) -> None:
    executable_path = tmp_path / "missing" / expected_executable_name(CURRENT_PLATFORM)
    candidate = _candidate(
        executable_path,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    version_probe = StubVersionProbe({})
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=version_probe,
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is None
    assert result.all_candidates[0].supported is False
    assert "does not exist" in result.all_candidates[0].diagnostics[0]
    assert version_probe.calls == []


def test_composite_locator_rejects_directory_candidates(tmp_path: Path) -> None:
    directory_path = tmp_path / "not-a-file"
    directory_path.mkdir()
    candidate = _candidate(
        directory_path,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=StubVersionProbe({}),
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is None
    assert "is not a file" in result.all_candidates[0].diagnostics[0]


def test_composite_locator_rejects_invalid_executable_files(tmp_path: Path) -> None:
    if CURRENT_PLATFORM is EnergyPlusPlatform.WINDOWS:
        invalid_path = _make_non_executable(tmp_path / "invalid" / "energyplus.txt")
    else:
        invalid_path = _make_non_executable(tmp_path / "invalid" / "energyplus")

    candidate = _candidate(
        invalid_path,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    version_probe = StubVersionProbe({})
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=version_probe,
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is None
    assert result.all_candidates[0].supported is False
    assert version_probe.calls == []


def test_composite_locator_checks_non_windows_executable_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable_path = _make_executable(tmp_path / "linux" / "energyplus")
    candidate = EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
        root_path=executable_path.parent,
        executable_path=executable_path,
        platform=EnergyPlusPlatform.LINUX,
    )
    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.composite_locator.os.access",
        lambda *_args: False,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((candidate,)),
        version_probe=StubVersionProbe({}),
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is None
    assert "is not executable" in result.all_candidates[0].diagnostics[0]


def test_composite_locator_prefers_the_configured_executable(tmp_path: Path) -> None:
    explicit_executable = _make_executable(
        tmp_path / "configured" / expected_executable_name(CURRENT_PLATFORM)
    )
    discovered_executable = _make_executable(
        tmp_path / "discovered" / expected_executable_name(CURRENT_PLATFORM)
    )
    explicit_candidate = _candidate(
        explicit_executable,
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
    )
    discovered_candidate = _candidate(
        discovered_executable,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((explicit_candidate, discovered_candidate)),
        version_probe=StubVersionProbe(
            {
                str(explicit_executable): VersionProbeResult(
                    version="24.2.0",
                    supported=True,
                ),
                str(discovered_executable): VersionProbeResult(
                    version="25.1.0",
                    supported=True,
                ),
            }
        ),
    )

    result = locator.locate(EnergyPlusSettings(executable_path=explicit_executable))

    assert result.selected_candidate is not None
    assert result.selected_candidate.executable_path == explicit_executable
    assert "explicitly configured EnergyPlus executable" in result.selection_diagnostics[-1]


def test_composite_locator_prefers_the_requested_version(tmp_path: Path) -> None:
    preferred_executable = _make_executable(
        tmp_path / "preferred" / expected_executable_name(CURRENT_PLATFORM)
    )
    newest_executable = _make_executable(
        tmp_path / "newest" / expected_executable_name(CURRENT_PLATFORM)
    )
    preferred_candidate = _candidate(
        preferred_executable,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    newest_candidate = _candidate(
        newest_executable,
        source=EnergyPlusCandidateSource.CONFIGURED_INSTALLATION_ROOT,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((newest_candidate, preferred_candidate)),
        version_probe=StubVersionProbe(
            {
                str(preferred_executable): VersionProbeResult(
                    version="24.2.0",
                    supported=True,
                ),
                str(newest_executable): VersionProbeResult(
                    version="25.1.0",
                    supported=True,
                ),
            }
        ),
    )

    result = locator.locate(EnergyPlusSettings(preferred_version="24.2"))

    assert result.selected_candidate is not None
    assert result.selected_candidate.executable_path == preferred_executable
    assert "preferred version 24.2" in result.selection_diagnostics[-1]


def test_composite_locator_selects_the_highest_supported_version(tmp_path: Path) -> None:
    older_executable = _make_executable(
        tmp_path / "older" / expected_executable_name(CURRENT_PLATFORM)
    )
    newer_executable = _make_executable(
        tmp_path / "newer" / expected_executable_name(CURRENT_PLATFORM)
    )
    older_candidate = _candidate(
        older_executable,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    newer_candidate = _candidate(
        newer_executable,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((older_candidate, newer_candidate)),
        version_probe=StubVersionProbe(
            {
                str(older_executable): VersionProbeResult(
                    version="24.2.0",
                    supported=True,
                ),
                str(newer_executable): VersionProbeResult(
                    version="25.1.0",
                    supported=True,
                ),
            }
        ),
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is not None
    assert result.selected_candidate.executable_path == newer_executable
    assert "highest supported EnergyPlus version" in result.selection_diagnostics[-1]


def test_composite_locator_uses_path_candidate_as_supported_fallback(tmp_path: Path) -> None:
    missing_executable = tmp_path / "missing" / expected_executable_name(CURRENT_PLATFORM)
    path_executable = _make_executable(
        tmp_path / "bin" / expected_executable_name(CURRENT_PLATFORM)
    )
    invalid_candidate = _candidate(
        missing_executable,
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
    )
    path_candidate = _candidate(path_executable, source=EnergyPlusCandidateSource.PATH)
    locator = CompositeEnergyPlusLocator(
        filesystem_probe=StubFilesystemProbe((invalid_candidate, path_candidate)),
        version_probe=StubVersionProbe(
            {
                str(path_executable): VersionProbeResult(
                    version="25.1.0",
                    supported=True,
                )
            }
        ),
    )

    result = locator.locate(EnergyPlusSettings())

    assert result.selected_candidate is not None
    assert result.selected_candidate.source is EnergyPlusCandidateSource.PATH
    assert "PATH-discovered" in result.selection_diagnostics[-1]
