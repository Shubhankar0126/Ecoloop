from __future__ import annotations

import os
from pathlib import Path

import pytest

from ecoloop_energyplus.infrastructure.validation.path_validator import PathValidator

PathLike = str | bytes | os.PathLike[str] | os.PathLike[bytes]


def _patch_access_denial(
    monkeypatch: pytest.MonkeyPatch,
    *,
    denied_path: Path,
    denied_mode: int,
) -> None:
    original_access = os.access

    def fake_access(path: PathLike, mode: int) -> bool:
        if str(path) == str(denied_path) and mode == denied_mode:
            return False

        return original_access(path, mode)

    monkeypatch.setattr(
        "ecoloop_energyplus.infrastructure.validation.path_validator.os.access",
        fake_access,
    )


def test_path_validator_accepts_existing_file_and_directory(tmp_path: Path) -> None:
    validator = PathValidator()
    file_path = tmp_path / "input.idf"
    file_path.write_text("Version, 25.1;", encoding="utf-8")

    assert validator.validate_file_exists(file_path).valid is True
    assert validator.validate_directory_exists(tmp_path).valid is True


def test_path_validator_reports_missing_file() -> None:
    result = PathValidator().validate_file_exists(Path("missing.idf"))

    assert result.valid is False
    assert result.issues[0].code == "path.missing"


def test_path_validator_reports_directory_for_file_check(tmp_path: Path) -> None:
    result = PathValidator().validate_file_exists(tmp_path)

    assert result.valid is False
    assert result.issues[0].code == "path.not_file"


def test_path_validator_reports_non_directory_path(tmp_path: Path) -> None:
    file_path = tmp_path / "output.txt"
    file_path.write_text("data", encoding="utf-8")

    result = PathValidator().validate_directory_exists(file_path)

    assert result.valid is False
    assert result.issues[0].code == "path.not_directory"


def test_path_validator_reports_unreadable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "input.idf"
    file_path.write_text("Version, 25.1;", encoding="utf-8")
    _patch_access_denial(
        monkeypatch,
        denied_path=file_path,
        denied_mode=os.R_OK,
    )

    result = PathValidator().validate_readable(file_path)

    assert result.valid is False
    assert result.issues[0].code == "path.not_readable"


def test_path_validator_reports_non_writable_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_access_denial(
        monkeypatch,
        denied_path=tmp_path,
        denied_mode=os.W_OK,
    )

    result = PathValidator().validate_writable(tmp_path)

    assert result.valid is False
    assert result.issues[0].code == "path.not_writable"


def test_path_validator_accepts_creatable_missing_path(tmp_path: Path) -> None:
    result = PathValidator().validate_creatable(tmp_path / "nested" / "output")

    assert result.valid is True


def test_path_validator_accepts_existing_creatable_path(tmp_path: Path) -> None:
    result = PathValidator().validate_creatable(tmp_path)

    assert result.valid is True


def test_path_validator_reports_non_creatable_path_for_non_writable_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_access_denial(
        monkeypatch,
        denied_path=tmp_path,
        denied_mode=os.W_OK,
    )

    result = PathValidator().validate_creatable(tmp_path / "nested" / "output")

    assert result.valid is False
    assert result.issues[0].code == "path.not_creatable"


def test_path_validator_reports_non_creatable_path_for_file_parent(tmp_path: Path) -> None:
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("data", encoding="utf-8")

    result = PathValidator().validate_creatable(blocking_file / "output")

    assert result.valid is False
    assert result.issues[0].code == "path.not_creatable"


def test_path_validator_reports_non_creatable_path_when_parent_lookup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = PathValidator()
    monkeypatch.setattr(validator, "_nearest_existing_parent", lambda _path: None)

    result = validator.validate_creatable(Path("unresolvable") / "output")

    assert result.valid is False
    assert result.issues[0].code == "path.not_creatable"


def test_path_validator_reports_non_executable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable_path = tmp_path / "energyplus"
    executable_path.write_text("binary", encoding="utf-8")
    _patch_access_denial(
        monkeypatch,
        denied_path=executable_path,
        denied_mode=os.X_OK,
    )

    result = PathValidator().validate_executable(executable_path)

    assert result.valid is False
    assert result.issues[0].code == "path.not_executable"


def test_path_validator_accepts_executable_file(tmp_path: Path) -> None:
    executable_path = tmp_path / "energyplus"
    executable_path.write_text("binary", encoding="utf-8")

    result = PathValidator().validate_executable(executable_path)

    assert result.valid is True


def test_path_validator_reports_missing_executable_path() -> None:
    result = PathValidator().validate_executable(Path("missing-executable"))

    assert result.valid is False
    assert result.issues[0].code == "path.missing"


def test_path_validator_reports_missing_path_for_readable_check() -> None:
    result = PathValidator().validate_readable(Path("missing-readable"))

    assert result.valid is False
    assert result.issues[0].code == "path.missing"


def test_path_validator_nearest_existing_parent_returns_current_directory() -> None:
    parent = PathValidator()._nearest_existing_parent(Path("missing-child"))

    assert parent == Path(".")


def test_path_validator_nearest_existing_parent_can_return_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "exists", lambda _self: False)

    parent = PathValidator()._nearest_existing_parent(Path("missing-child"))

    assert parent is None
