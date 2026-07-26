from __future__ import annotations

import os
from pathlib import Path

import pytest

from ecoloop_energyplus.config.models import EnergyPlusSettings
from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusPlatform,
    detect_platform_name,
    expected_executable_name,
)
from ecoloop_energyplus.infrastructure.locator.filesystem_probe import FilesystemProbe


def _create_candidate_file(root_path: Path, executable_name: str) -> Path:
    root_path.mkdir(parents=True, exist_ok=True)
    executable_path = root_path / executable_name
    executable_path.write_text("energyplus", encoding="utf-8")
    return executable_path


def test_filesystem_probe_discovers_candidates_in_priority_order(tmp_path: Path) -> None:
    platform = detect_platform_name()
    executable_name = expected_executable_name(platform)
    explicit_root = tmp_path / "explicit-install"
    env_root = tmp_path / "env-install"
    configured_root = tmp_path / "configured-install"
    standard_root = tmp_path / "EnergyPlus-25-1-0"
    path_root = tmp_path / "bin"

    explicit_executable = _create_candidate_file(explicit_root, executable_name)
    _create_candidate_file(env_root, executable_name)
    _create_candidate_file(configured_root, executable_name)
    _create_candidate_file(standard_root, executable_name)
    _create_candidate_file(path_root, executable_name)

    probe = FilesystemProbe(
        environment={
            "ENERGYPLUS_HOME": str(env_root),
            "PATH": str(path_root),
        },
        platform_name=platform,
        standard_search_patterns={platform: (str(tmp_path / "EnergyPlus-*"),)},
    )
    settings = EnergyPlusSettings(
        executable_path=explicit_executable,
        installation_roots=(configured_root,),
    )

    candidates = probe.discover(settings)

    assert [candidate.source for candidate in candidates] == [
        EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
        EnergyPlusCandidateSource.ENERGYPLUS_HOME,
        EnergyPlusCandidateSource.CONFIGURED_INSTALLATION_ROOT,
        EnergyPlusCandidateSource.STANDARD_DIRECTORY,
        EnergyPlusCandidateSource.PATH,
    ]


def test_filesystem_probe_skips_path_search_when_disabled(tmp_path: Path) -> None:
    platform = detect_platform_name()
    executable_name = expected_executable_name(platform)
    path_root = tmp_path / "bin"
    _create_candidate_file(path_root, executable_name)

    probe = FilesystemProbe(
        environment={"PATH": str(path_root)},
        platform_name=platform,
        standard_search_patterns={platform: ()},
    )
    settings = EnergyPlusSettings(discover_on_path=False)

    candidates = probe.discover(settings)

    assert candidates == ()


def test_filesystem_probe_reports_missing_explicit_and_home_candidates(tmp_path: Path) -> None:
    platform = detect_platform_name()
    executable_name = expected_executable_name(platform)
    missing_executable = tmp_path / "missing-install" / executable_name
    missing_home = tmp_path / "missing-home"
    probe = FilesystemProbe(
        environment={"ENERGYPLUS_HOME": str(missing_home), "PATH": ""},
        platform_name=platform,
        standard_search_patterns={platform: ()},
    )
    settings = EnergyPlusSettings(executable_path=missing_executable)

    candidates = probe.discover(settings)

    assert len(candidates) == 2
    assert candidates[0].executable_path == missing_executable
    assert candidates[1].root_path == missing_home


def test_filesystem_probe_default_patterns_cover_supported_platforms() -> None:
    assert FilesystemProbe(platform_name=EnergyPlusPlatform.WINDOWS)._standard_patterns() == (
        r"C:\EnergyPlusV*",
    )
    assert FilesystemProbe(platform_name=EnergyPlusPlatform.MACOS)._standard_patterns() == (
        "/Applications/EnergyPlus-*",
    )
    assert FilesystemProbe(platform_name=EnergyPlusPlatform.LINUX)._standard_patterns() == (
        "/usr/local/EnergyPlus-*",
        "/opt/EnergyPlus-*",
    )


def test_filesystem_probe_reads_process_environment_when_not_injected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    platform = detect_platform_name()
    executable_name = expected_executable_name(platform)
    env_root = tmp_path / "env-root"
    path_root = tmp_path / "bin"
    _create_candidate_file(env_root, executable_name)
    _create_candidate_file(path_root, executable_name)
    monkeypatch.setenv("ENERGYPLUS_HOME", str(env_root))
    monkeypatch.setenv("PATH", str(path_root))

    probe = FilesystemProbe(
        platform_name=platform,
        standard_search_patterns={platform: ()},
    )
    candidates = probe.discover(EnergyPlusSettings())

    assert [candidate.source for candidate in candidates] == [
        EnergyPlusCandidateSource.ENERGYPLUS_HOME,
        EnergyPlusCandidateSource.PATH,
    ]


def test_filesystem_probe_ignores_blank_and_missing_path_entries(tmp_path: Path) -> None:
    platform = detect_platform_name()
    executable_name = expected_executable_name(platform)
    path_root = tmp_path / "bin"
    _create_candidate_file(path_root, executable_name)
    probe = FilesystemProbe(
        environment={
            "PATH": f"  {os.pathsep}{tmp_path / 'missing'}{os.pathsep}{path_root}",
        },
        platform_name=platform,
        standard_search_patterns={platform: ()},
    )

    candidates = probe.discover(EnergyPlusSettings())

    assert [candidate.source for candidate in candidates] == [
        EnergyPlusCandidateSource.PATH,
    ]
