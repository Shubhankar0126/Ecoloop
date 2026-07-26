from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from ecoloop_energyplus.config.models import SimulationSettings
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.validation.input_validator import InputValidator
from ecoloop_energyplus.infrastructure.validation.path_validator import PathValidator
from ecoloop_energyplus.infrastructure.validation.validation_result import ValidationResult

PathLike = str | bytes | os.PathLike[str] | os.PathLike[bytes]


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _patch_read_denial(
    monkeypatch: pytest.MonkeyPatch,
    *,
    denied_path: Path,
) -> None:
    original_access = os.access

    def fake_access(path: PathLike, mode: int) -> bool:
        if str(path) == str(denied_path) and mode == os.R_OK:
            return False

        return original_access(path, mode)

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.validation.path_validator.os.access",
        fake_access,
    )


def _settings() -> SimulationSettings:
    return SimulationSettings(
        default_timeout_seconds=1200,
        maximum_timeout_seconds=3600,
        default_parallel_jobs=1,
        maximum_parallel_jobs=4,
    )


def test_input_validator_accepts_valid_simulation_spec(tmp_path: Path) -> None:
    idf_path = _write_text(
        tmp_path / "building.idf",
        "! comment\nVersion,25.1;\nBuilding,Example;\n",
    )
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\nDATA\n",
    )
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is True
    assert result.issues == ()
    assert result.warnings == ()


def test_input_validator_reports_missing_idf(tmp_path: Path) -> None:
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    spec = SimulationSpec(idf_path=tmp_path / "missing.idf", epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert result.issues[0].target == "simulation_spec.idf_path"


def test_input_validator_reports_unreadable_idf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    _patch_read_denial(monkeypatch, denied_path=idf_path)
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "path.not_readable" for issue in result.issues)


def test_input_validator_reports_empty_idf(tmp_path: Path) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.idf.empty" for issue in result.issues)


def test_input_validator_reports_missing_epw(tmp_path: Path) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    spec = SimulationSpec(idf_path=idf_path, epw_path=tmp_path / "missing.epw")

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.target == "simulation_spec.epw_path" for issue in result.issues)


def test_input_validator_reports_invalid_epw_header(tmp_path: Path) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(tmp_path / "weather.epw", "INVALID,HEADER\n")
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.epw.invalid_header" for issue in result.issues)


def test_input_validator_reports_timeout_validation_errors(tmp_path: Path) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    invalid_spec = SimulationSpec(
        idf_path=idf_path,
        epw_path=epw_path,
        timeout_seconds=0,
    )
    excessive_spec = SimulationSpec(
        idf_path=idf_path,
        epw_path=epw_path,
        timeout_seconds=7200,
    )
    validator = InputValidator()

    invalid_result = validator.validate(invalid_spec, _settings())
    excessive_result = validator.validate(excessive_spec, _settings())

    assert any(issue.code == "simulation.timeout.invalid" for issue in invalid_result.issues)
    assert any(
        issue.code == "simulation.timeout.exceeds_maximum"
        for issue in excessive_result.issues
    )


def test_input_validator_reports_parallel_job_validation_errors(tmp_path: Path) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    invalid_spec = SimulationSpec(
        idf_path=idf_path,
        epw_path=epw_path,
        parallel_jobs=0,
    )
    excessive_spec = SimulationSpec(
        idf_path=idf_path,
        epw_path=epw_path,
        parallel_jobs=8,
    )
    validator = InputValidator()

    invalid_result = validator.validate(invalid_spec, _settings())
    excessive_result = validator.validate(excessive_spec, _settings())

    assert any(
        issue.code == "simulation.parallel_jobs.invalid"
        for issue in invalid_result.issues
    )
    assert any(
        issue.code == "simulation.parallel_jobs.exceeds_maximum"
        for issue in excessive_result.issues
    )


def test_input_validator_reports_missing_idf_version_object_with_bounded_scan(
    tmp_path: Path,
) -> None:
    idf_path = _write_text(
        tmp_path / "building.idf",
        "! comment\nBuilding,Example;\nZone,Office;\nVersion,25.1;\n",
    )
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator(idf_scan_line_limit=2).validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.idf.missing_version_object" for issue in result.issues)


def test_input_validator_reports_idf_scan_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    original_open = Path.open

    def fake_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == idf_path:
            raise OSError("scan failed")

        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.idf.scan_failed" for issue in result.issues)


def test_input_validator_reports_epw_header_read_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    original_open = Path.open

    def fake_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == epw_path:
            raise OSError("header failed")

        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator().validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.epw.header_read_failed" for issue in result.issues)


def test_input_validator_reports_input_stat_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    idf_path = _write_text(tmp_path / "building.idf", "Version,25.1;\n")
    epw_path = _write_text(
        tmp_path / "weather.epw",
        "LOCATION,Test City,Test State,IN,TMY,123456,12.00,77.00,5.5,800.0\n",
    )
    original_stat = Path.stat

    class AlwaysValidPathValidator(PathValidator):
        def validate_file_exists(
            self,
            path: Path,
            *,
            target: str | None = None,
        ) -> ValidationResult:
            return ValidationResult.success()

        def validate_readable(
            self,
            path: Path,
            *,
            target: str | None = None,
        ) -> ValidationResult:
            return ValidationResult.success()

    def fake_stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == idf_path:
            raise OSError("stat failed")

        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    result = InputValidator(path_validator=AlwaysValidPathValidator()).validate(spec, _settings())

    assert result.valid is False
    assert any(issue.code == "simulation.input.stat_failed" for issue in result.issues)
