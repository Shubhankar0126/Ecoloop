from __future__ import annotations

from pathlib import Path

from ecoloop_energyplus.infrastructure.locator.candidate import (
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusPlatform,
    build_installation_id,
    candidate_path_key,
    detect_platform_name,
    expected_executable_name,
)


def test_detect_platform_name_maps_supported_platform_identifiers() -> None:
    assert detect_platform_name("win32") is EnergyPlusPlatform.WINDOWS
    assert detect_platform_name("darwin") is EnergyPlusPlatform.MACOS
    assert detect_platform_name("linux") is EnergyPlusPlatform.LINUX


def test_candidate_create_builds_stable_identifier_and_idd_path() -> None:
    executable_path = Path("C:/EnergyPlusV25-1-0/energyplus.exe")
    candidate = EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
        root_path=executable_path.parent,
        executable_path=executable_path,
        platform=EnergyPlusPlatform.WINDOWS,
    )

    assert candidate.installation_id == build_installation_id(
        executable_path,
        EnergyPlusPlatform.WINDOWS,
    )
    assert candidate.idd_path == Path("C:/EnergyPlusV25-1-0/Energy+.idd")


def test_candidate_path_key_is_case_insensitive_on_windows() -> None:
    upper_case_key = candidate_path_key(
        Path("C:/EnergyPlusV25-1-0/ENERGYPLUS.EXE"),
        EnergyPlusPlatform.WINDOWS,
    )
    lower_case_key = candidate_path_key(
        Path("C:/energyplusv25-1-0/energyplus.exe"),
        EnergyPlusPlatform.WINDOWS,
    )

    assert upper_case_key == lower_case_key


def test_non_windows_candidate_helpers_preserve_unix_style_paths() -> None:
    assert expected_executable_name(EnergyPlusPlatform.LINUX) == "energyplus"
    assert candidate_path_key(
        Path("/opt/EnergyPlus-25-1-0/energyplus"),
        EnergyPlusPlatform.LINUX,
    ) == "/opt/EnergyPlus-25-1-0/energyplus"
