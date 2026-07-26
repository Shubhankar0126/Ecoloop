"""Run-directory and artifact management for EnergyPlus simulation outputs."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from hashlib import new as new_hash
from pathlib import Path
from uuid import uuid4

from ecoloop_energyplus.config.models import OutputSettings
from ecoloop_energyplus.domain.enums import SimulationStatus
from ecoloop_energyplus.domain.exceptions import EnergyPlusConfigurationError
from ecoloop_energyplus.domain.models import SimulationArtifact, SimulationSpec
from ecoloop_energyplus.infrastructure.output.artifact_manifest import (
    ArtifactManifest,
    build_artifact_id,
    classify_artifact_kind,
    guess_media_type,
)
from ecoloop_energyplus.infrastructure.output.cleanup import CleanupManager, CleanupResult
from ecoloop_energyplus.infrastructure.output.run_directory import RunDirectory


class OutputManager:
    """Manage isolated directories and artifact manifests for EnergyPlus runs."""

    def __init__(
        self,
        settings: OutputSettings,
        *,
        cleanup_manager: CleanupManager | None = None,
    ) -> None:
        """Initialize the output manager with immutable settings."""
        self._settings = settings
        self._cleanup_manager = cleanup_manager or CleanupManager()

    def create_run_directory(
        self,
        *,
        run_id: str | None = None,
        prefix: str = "run",
    ) -> RunDirectory:
        """Create an isolated run directory with stable subdirectories."""
        created_at = datetime.now(tz=UTC)
        normalized_run_id = run_id or uuid4().hex
        directory_name = f"{prefix}-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{normalized_run_id}"
        root_path = self._settings.root_directory / directory_name
        input_path = root_path / "input"
        output_path = root_path / "output"
        logs_path = root_path / "logs"
        metadata_path = root_path / "metadata"

        for path in (input_path, output_path, logs_path, metadata_path):
            path.mkdir(parents=True, exist_ok=False)

        return RunDirectory(
            run_id=normalized_run_id,
            root_path=root_path,
            input_path=input_path,
            output_path=output_path,
            logs_path=logs_path,
            metadata_path=metadata_path,
            stdout_path=logs_path / "stdout.log",
            stderr_path=logs_path / "stderr.log",
            manifest_path=metadata_path / "artifact-manifest.json",
            created_at=created_at,
        )

    def stage_input_artifacts(
        self,
        run_directory: RunDirectory,
        spec: SimulationSpec,
    ) -> tuple[SimulationArtifact, ...]:
        """Copy input artifacts into the run directory when configured to preserve them."""
        if not self._settings.preserve_input_copies:
            return ()

        staged_paths = (
            (spec.idf_path, run_directory.input_path / spec.idf_path.name),
            (spec.epw_path, run_directory.input_path / spec.epw_path.name),
        )
        artifacts: list[SimulationArtifact] = []

        for source_path, destination_path in staged_paths:
            shutil.copy2(source_path, destination_path)
            relative_path = destination_path.relative_to(run_directory.root_path)
            artifacts.append(
                self._build_artifact(
                    relative_path=relative_path,
                    absolute_path=destination_path,
                )
            )

        return tuple(artifacts)

    def build_artifact_manifest(self, run_directory: RunDirectory) -> ArtifactManifest:
        """Build an artifact manifest by scanning one isolated run directory."""
        artifacts = tuple(
            self._build_artifact(
                relative_path=path.relative_to(run_directory.root_path),
                absolute_path=path,
            )
            for path in sorted(run_directory.root_path.rglob("*"))
            if path.is_file() and path != run_directory.manifest_path
        )
        return ArtifactManifest(
            run_id=run_directory.run_id,
            run_directory=run_directory.root_path,
            generated_at=datetime.now(tz=UTC),
            checksum_algorithm=self._settings.checksum_algorithm,
            artifacts=artifacts,
        )

    def write_artifact_manifest(self, run_directory: RunDirectory) -> ArtifactManifest:
        """Generate and persist an artifact manifest for one run directory."""
        manifest = self.build_artifact_manifest(run_directory)
        run_directory.manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return manifest

    def cleanup_run_directory(
        self,
        run_directory: RunDirectory,
        *,
        status: SimulationStatus,
        completed_at: datetime | None = None,
        now: datetime | None = None,
        force: bool = False,
    ) -> CleanupResult:
        """Apply retention or forced cleanup to one run directory."""
        return self._cleanup_manager.cleanup(
            run_directory,
            status=status,
            settings=self._settings,
            completed_at=completed_at,
            now=now,
            force=force,
        )

    def _build_artifact(
        self,
        *,
        relative_path: Path,
        absolute_path: Path,
    ) -> SimulationArtifact:
        """Build one normalized artifact metadata record from a filesystem path."""
        return SimulationArtifact(
            artifact_id=build_artifact_id(relative_path),
            kind=classify_artifact_kind(relative_path),
            relative_path=relative_path,
            media_type=guess_media_type(relative_path),
            size_bytes=absolute_path.stat().st_size,
            checksum=self._calculate_checksum(absolute_path),
        )

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate a checksum for one artifact using the configured algorithm."""
        try:
            digest = new_hash(self._settings.checksum_algorithm)
        except ValueError as error:
            raise EnergyPlusConfigurationError(
                message=(
                    "EnergyPlus output checksum algorithm is invalid: "
                    f"{self._settings.checksum_algorithm}."
                ),
                context={"checksum_algorithm": self._settings.checksum_algorithm},
            ) from error

        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)

        return digest.hexdigest()


__all__ = ["OutputManager"]
