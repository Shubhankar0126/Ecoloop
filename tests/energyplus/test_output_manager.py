from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ecoloop_energyplus.config.models import OutputSettings
from ecoloop_energyplus.domain.enums import SimulationArtifactKind, SimulationStatus
from ecoloop_energyplus.domain.exceptions import EnergyPlusConfigurationError
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.output import (
    ArtifactManifest,
    CleanupManager,
    OutputManager,
    RunDirectory,
)
from ecoloop_energyplus.infrastructure.output.artifact_manifest import (
    classify_artifact_kind,
    guess_media_type,
)


def _output_settings(
    root_directory: Path,
    *,
    preserve_input_copies: bool = True,
    checksum_algorithm: str = "sha256",
    retention_success_days: int = 7,
    retention_failure_days: int = 30,
    cleanup_on_success: bool = False,
    cleanup_on_failure: bool = False,
) -> OutputSettings:
    return OutputSettings(
        root_directory=root_directory,
        preserve_input_copies=preserve_input_copies,
        checksum_algorithm=checksum_algorithm,
        retention_success_days=retention_success_days,
        retention_failure_days=retention_failure_days,
        cleanup_on_success=cleanup_on_success,
        cleanup_on_failure=cleanup_on_failure,
    )


def test_output_manager_creates_isolated_run_directory(tmp_path: Path) -> None:
    manager = OutputManager(_output_settings(tmp_path / "runs"))

    run_directory = manager.create_run_directory(run_id="test-run")

    assert run_directory.run_id == "test-run"
    assert run_directory.input_path.exists()
    assert run_directory.output_path.exists()
    assert run_directory.logs_path.exists()
    assert run_directory.metadata_path.exists()
    assert "test-run" in run_directory.root_path.name


def test_output_manager_stages_inputs_and_writes_artifact_manifest(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    manager = OutputManager(_output_settings(output_root))
    run_directory = manager.create_run_directory(run_id="manifest-run")
    idf_path = tmp_path / "building.idf"
    epw_path = tmp_path / "weather.epw"
    idf_path.write_text("Version,25.1;\n", encoding="utf-8")
    epw_path.write_text("LOCATION,Test\n", encoding="utf-8")
    spec = SimulationSpec(idf_path=idf_path, epw_path=epw_path)

    staged_artifacts = manager.stage_input_artifacts(run_directory, spec)
    (run_directory.output_path / "eplusout.err").write_text(
        "** Warning ** sample warning\n",
        encoding="utf-8",
    )
    (run_directory.output_path / "eplusout.sql").write_text("sqlite", encoding="utf-8")
    run_directory.stdout_path.write_text("stdout", encoding="utf-8")
    manifest = manager.write_artifact_manifest(run_directory)

    assert len(staged_artifacts) == 2
    assert manifest.run_id == "manifest-run"
    assert run_directory.manifest_path.exists()
    artifact_kinds = {artifact.kind for artifact in manifest.artifacts}
    assert SimulationArtifactKind.INPUT in artifact_kinds
    assert SimulationArtifactKind.DIAGNOSTIC in artifact_kinds
    assert SimulationArtifactKind.DATABASE in artifact_kinds
    assert SimulationArtifactKind.LOG in artifact_kinds
    assert all(artifact.checksum for artifact in manifest.artifacts)
    assert all(
        artifact.relative_path != Path("metadata/artifact-manifest.json")
        for artifact in manifest.artifacts
    )


def test_output_manager_skips_input_staging_when_disabled(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    manager = OutputManager(
        _output_settings(output_root, preserve_input_copies=False)
    )
    run_directory = manager.create_run_directory(run_id="no-stage")
    idf_path = tmp_path / "building.idf"
    epw_path = tmp_path / "weather.epw"
    idf_path.write_text("Version,25.1;\n", encoding="utf-8")
    epw_path.write_text("LOCATION,Test\n", encoding="utf-8")

    artifacts = manager.stage_input_artifacts(
        run_directory,
        SimulationSpec(idf_path=idf_path, epw_path=epw_path),
    )

    assert artifacts == ()
    assert list(run_directory.input_path.iterdir()) == []


def test_output_manager_raises_for_invalid_checksum_algorithm(tmp_path: Path) -> None:
    manager = OutputManager(
        _output_settings(tmp_path / "runs", checksum_algorithm="invalid-checksum")
    )
    run_directory = manager.create_run_directory(run_id="checksum-run")
    file_path = run_directory.output_path / "eplusout.err"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(EnergyPlusConfigurationError, match="checksum algorithm is invalid"):
        manager.build_artifact_manifest(run_directory)


def test_cleanup_manager_removes_directory_when_forced(tmp_path: Path) -> None:
    manager = OutputManager(_output_settings(tmp_path / "runs"))
    run_directory = manager.create_run_directory(run_id="force-cleanup")

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        force=True,
    )

    assert result.removed is True
    assert run_directory.root_path.exists() is False


def test_cleanup_manager_removes_expired_successful_runs(tmp_path: Path) -> None:
    manager = OutputManager(
        _output_settings(tmp_path / "runs", retention_success_days=1, cleanup_on_success=False)
    )
    run_directory = manager.create_run_directory(run_id="expired-success")
    completed_at = datetime.now(tz=UTC) - timedelta(days=2)

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        completed_at=completed_at,
        now=datetime.now(tz=UTC),
    )

    assert result.removed is True
    assert "retention period" in result.reason


def test_cleanup_manager_removes_successful_runs_when_configured(tmp_path: Path) -> None:
    manager = OutputManager(
        _output_settings(tmp_path / "runs", cleanup_on_success=True)
    )
    run_directory = manager.create_run_directory(run_id="success-cleanup")

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
    )

    assert result.removed is True
    assert "successful run" in result.reason


def test_cleanup_manager_removes_failed_runs_when_configured(tmp_path: Path) -> None:
    manager = OutputManager(
        _output_settings(tmp_path / "runs", cleanup_on_failure=True)
    )
    run_directory = manager.create_run_directory(run_id="failed-cleanup")

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.FAILED,
    )

    assert result.removed is True
    assert "failed run" in result.reason


def test_cleanup_manager_skips_recent_or_non_terminal_runs(tmp_path: Path) -> None:
    manager = OutputManager(
        _output_settings(tmp_path / "runs", retention_success_days=5, cleanup_on_success=False)
    )
    run_directory = manager.create_run_directory(run_id="retained-run")
    completed_at = datetime.now(tz=UTC)

    recent_result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        completed_at=completed_at,
        now=completed_at + timedelta(hours=1),
    )
    non_terminal_result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.RUNNING,
        completed_at=None,
        now=completed_at + timedelta(hours=1),
    )

    assert recent_result.removed is False
    assert non_terminal_result.removed is False
    assert run_directory.root_path.exists() is True


def test_cleanup_manager_handles_missing_directory(tmp_path: Path) -> None:
    manager = OutputManager(_output_settings(tmp_path / "runs"))
    run_directory = manager.create_run_directory(run_id="missing-run")
    manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        force=True,
    )

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        force=True,
    )

    assert result.removed is False
    assert result.reason == "Run directory does not exist."


def test_cleanup_manager_returns_retention_result_when_completion_time_is_missing(
    tmp_path: Path,
) -> None:
    cleanup_manager = CleanupManager()
    manager = OutputManager(_output_settings(tmp_path / "runs"), cleanup_manager=cleanup_manager)
    run_directory = manager.create_run_directory(run_id="missing-completion")

    result = manager.cleanup_run_directory(
        run_directory,
        status=SimulationStatus.SUCCEEDED,
        completed_at=None,
        force=False,
    )

    assert result.removed is False
    assert "retention policy" in result.reason


def test_artifact_classification_helpers_cover_expected_suffixes() -> None:
    assert classify_artifact_kind(Path("input/building.idf")) is SimulationArtifactKind.INPUT
    assert classify_artifact_kind(Path("output/eplusout.err")) is SimulationArtifactKind.DIAGNOSTIC
    assert classify_artifact_kind(Path("output/eplusout.eso")) is SimulationArtifactKind.TIME_SERIES
    assert classify_artifact_kind(Path("output/eplusout.csv")) is SimulationArtifactKind.TABULAR
    assert classify_artifact_kind(Path("logs/stdout.log")) is SimulationArtifactKind.LOG
    assert classify_artifact_kind(Path("metadata/manifest.json")) is SimulationArtifactKind.METADATA
    assert classify_artifact_kind(Path("output/custom.bin")) is SimulationArtifactKind.OTHER
    assert guess_media_type(Path("output/eplusout.sql")) == "application/vnd.sqlite3"
    assert guess_media_type(Path("output/custom.energyplus")) is None


def test_artifact_manifest_requires_timezone_aware_generated_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ArtifactManifest(
            run_id="manifest",
            run_directory=Path("runs/manifest"),
            generated_at=datetime.now(),
            checksum_algorithm="sha256",
        )


def test_run_directory_requires_timezone_aware_created_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        RunDirectory(
            run_id="run",
            root_path=Path("runs/run"),
            input_path=Path("runs/run/input"),
            output_path=Path("runs/run/output"),
            logs_path=Path("runs/run/logs"),
            metadata_path=Path("runs/run/metadata"),
            stdout_path=Path("runs/run/logs/stdout.log"),
            stderr_path=Path("runs/run/logs/stderr.log"),
            manifest_path=Path("runs/run/metadata/artifact-manifest.json"),
            created_at=datetime.now(),
        )
