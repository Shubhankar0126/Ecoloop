from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ecoloop_energyplus.infrastructure.locator.version_probe import VersionProbe, parse_version_key


def test_parse_version_key_normalizes_energyplus_versions() -> None:
    assert parse_version_key("25.1.0") == (25, 1)
    assert parse_version_key("EnergyPlus 24.2.1") == (24, 2, 1)
    assert parse_version_key("invalid") is None


def test_version_probe_parses_supported_version(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_commands: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        recorded_commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="EnergyPlus, Version 25.1.0-87f1cbeebb",
            stderr="",
        )

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.version_probe.subprocess.run",
        fake_run,
    )

    executable_path = Path("/opt/energyplus")
    result = VersionProbe(timeout_seconds=4).probe(executable_path)

    assert recorded_commands == [[str(executable_path), "--version"]]
    assert result.version == "25.1.0"
    assert result.supported is True
    assert result.diagnostics == ()


def test_version_probe_marks_versions_below_minimum_as_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="EnergyPlus Version 22.2.0",
            stderr="",
        )

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.version_probe.subprocess.run",
        fake_run,
    )

    result = VersionProbe().probe(
        Path("/opt/energyplus"),
        minimum_supported_version="23.1.0",
    )

    assert result.version == "22.2.0"
    assert result.supported is False
    assert "minimum supported version 23.1.0" in result.diagnostics[0]


def test_version_probe_reports_non_zero_exit_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=2,
            stdout="EnergyPlus Version 25.1.0",
            stderr="unexpected failure",
        )

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.version_probe.subprocess.run",
        fake_run,
    )

    result = VersionProbe().probe(Path("/opt/energyplus"))

    assert result.version == "25.1.0"
    assert result.supported is False
    assert result.diagnostics == ("EnergyPlus version command returned exit code 2.",)


def test_version_probe_reports_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="not a version",
            stderr="",
        )

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.version_probe.subprocess.run",
        fake_run,
    )

    result = VersionProbe().probe(Path("/opt/energyplus"))

    assert result.version is None
    assert result.supported is False
    assert result.diagnostics == ("EnergyPlus version output did not include a parseable version.",)


@pytest.mark.parametrize(
    ("raised_exception", "expected_message"),
    [
        (
            subprocess.TimeoutExpired(cmd=["energyplus", "--version"], timeout=5),
            "timed out after 5 seconds",
        ),
        (
            OSError("permission denied"),
            "Failed to execute EnergyPlus version command: permission denied.",
        ),
    ],
)
def test_version_probe_reports_process_failures(
    monkeypatch: pytest.MonkeyPatch,
    raised_exception: Exception,
    expected_message: str,
) -> None:
    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise raised_exception

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.locator.version_probe.subprocess.run",
        fake_run,
    )

    result = VersionProbe(timeout_seconds=5).probe(Path("/opt/energyplus"))

    assert result.version is None
    assert result.supported is False
    assert expected_message in result.diagnostics[0]
