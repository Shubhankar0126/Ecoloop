from __future__ import annotations

import os
from pathlib import Path

import pytest

from ecoloop_energyplus.config.models import (
    EnergyPlusPlatformConfig,
    EnergyPlusSettings,
    OutputSettings,
    SimulationSettings,
)
from ecoloop_energyplus.infrastructure.locator import (
    CompositeEnergyPlusLocator,
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
    EnergyPlusLocatorResult,
)
from ecoloop_energyplus.infrastructure.locator.candidate import (
    detect_platform_name,
    expected_executable_name,
)
from ecoloop_energyplus.infrastructure.validation.startup_validator import StartupValidator

PathLike = str | bytes | os.PathLike[str] | os.PathLike[bytes]
CURRENT_PLATFORM = detect_platform_name()


def _patch_write_denial(
    monkeypatch: pytest.MonkeyPatch,
    *,
    denied_path: Path,
) -> None:
    original_access = os.access

    def fake_access(path: PathLike, mode: int) -> bool:
        if str(path) == str(denied_path) and mode == os.W_OK:
            return False

        return original_access(path, mode)

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.validation.path_validator.os.access",
        fake_access,
    )


def _candidate(
    executable_path: Path,
    *,
    supported: bool | None,
    diagnostics: tuple[str, ...] = (),
    version: str | None = "25.1.0",
) -> EnergyPlusInstallationCandidate:
    executable_path.parent.mkdir(parents=True, exist_ok=True)
    executable_path.write_text("energyplus", encoding="utf-8")
    return EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.STANDARD_DIRECTORY,
        root_path=executable_path.parent,
        executable_path=executable_path,
        platform=CURRENT_PLATFORM,
        supported=supported,
        version=version,
        diagnostics=diagnostics,
    )


def _config(
    output_root: Path,
    *,
    energyplus: EnergyPlusSettings | None = None,
) -> EnergyPlusPlatformConfig:
    return EnergyPlusPlatformConfig(
        energyplus=energyplus or EnergyPlusSettings(),
        simulation=SimulationSettings(),
        output=OutputSettings(root_directory=output_root),
    )


class StubLocator(CompositeEnergyPlusLocator):
    def __init__(self, result: EnergyPlusLocatorResult) -> None:
        self._result = result

    def locate(self, settings: EnergyPlusSettings) -> EnergyPlusLocatorResult:
        return self._result


def test_startup_validator_reports_success_for_ready_platform(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    discarded_candidate = _candidate(
        tmp_path / "EnergyPlusV22-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=False,
        diagnostics=("EnergyPlus version 22.1.0 is below the minimum supported version 23.1.0.",),
        version="22.1.0",
    )
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate, discarded_candidate),
            selection_diagnostics=("Selected the highest supported EnergyPlus version.",),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is True
    assert result.issues == ()
    assert any(
        warning.code == "startup.energyplus.candidate_discarded"
        for warning in result.warnings
    )


def test_startup_validator_reports_missing_supported_installation(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=None,
            all_candidates=(),
            selection_diagnostics=(
                "Configured executable path does not exist.",
                "No supported EnergyPlus installation was found.",
            ),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is False
    assert result.issues[0].code == "startup.energyplus.installation_unavailable"
    assert any(
        warning.code == "startup.energyplus.locator_diagnostic"
        for warning in result.warnings
    )


def test_startup_validator_reports_non_writable_output_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    _patch_write_denial(monkeypatch, denied_path=output_root)
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is False
    assert any(issue.code == "path.not_writable" for issue in result.issues)


def test_startup_validator_reports_version_configuration_conflicts(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )
    config = _config(
        output_root,
        energyplus=EnergyPlusSettings(
            preferred_version="22.1.0",
            minimum_supported_version="23.1.0",
        ),
    )

    result = StartupValidator(locator=locator).validate(config)

    assert result.valid is False
    assert any(
        issue.code == "startup.configuration.preferred_version_below_minimum"
        for issue in result.issues
    )


def test_startup_validator_reports_unparseable_version_strings(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )
    config = _config(
        output_root,
        energyplus=EnergyPlusSettings(
            preferred_version="not-a-version",
            minimum_supported_version="also-bad",
        ),
    )

    result = StartupValidator(locator=locator).validate(config)

    assert result.valid is False
    assert any(
        issue.code == "startup.configuration.invalid_preferred_version"
        for issue in result.issues
    )
    assert any(
        issue.code == "startup.configuration.invalid_minimum_supported_version"
        for issue in result.issues
    )


def test_startup_validator_warns_when_output_root_is_creatable(tmp_path: Path) -> None:
    output_root = tmp_path / "future-output"
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is True
    assert any(warning.code == "startup.output_root.creatable" for warning in result.warnings)


def test_startup_validator_reports_output_root_that_is_not_a_directory(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output.txt"
    output_root.write_text("data", encoding="utf-8")
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is False
    assert any(issue.code == "path.not_directory" for issue in result.issues)


def test_startup_validator_reports_non_creatable_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "nested" / "future-output"
    selected_candidate = _candidate(
        tmp_path / "EnergyPlusV25-1-0" / expected_executable_name(CURRENT_PLATFORM),
        supported=True,
    )
    _patch_write_denial(monkeypatch, denied_path=tmp_path)
    locator = StubLocator(
        EnergyPlusLocatorResult(
            selected_candidate=selected_candidate,
            all_candidates=(selected_candidate,),
            selection_diagnostics=(),
        )
    )

    result = StartupValidator(locator=locator).validate(_config(output_root))

    assert result.valid is False
    assert any(issue.code == "path.not_creatable" for issue in result.issues)


def test_startup_validator_warns_when_energyplus_is_disabled(tmp_path: Path) -> None:
    config = _config(
        tmp_path / "output",
        energyplus=EnergyPlusSettings(enabled=False),
    )

    result = StartupValidator().validate(config)

    assert result.valid is True
    assert result.issues == ()
    assert result.warnings[0].code == "startup.energyplus.disabled"
