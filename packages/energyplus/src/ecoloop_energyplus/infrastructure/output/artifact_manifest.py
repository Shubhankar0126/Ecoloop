"""Artifact manifest models and classification helpers for EnergyPlus runs."""

from __future__ import annotations

import mimetypes
from datetime import datetime
from hashlib import sha1
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ecoloop_energyplus.domain.enums import SimulationArtifactKind
from ecoloop_energyplus.domain.models import SimulationArtifact


def _ensure_aware_datetime(value: datetime) -> datetime:
    """Require timezone-aware datetimes in artifact manifest models."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must be timezone-aware.")

    return value


class ArtifactManifest(BaseModel):
    """Immutable manifest of artifacts stored for one EnergyPlus run."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    run_directory: Path
    generated_at: datetime
    checksum_algorithm: str = Field(min_length=1)
    artifacts: tuple[SimulationArtifact, ...] = ()

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: datetime) -> datetime:
        """Ensure the manifest timestamp remains timezone-aware."""
        return _ensure_aware_datetime(value)


def build_artifact_id(relative_path: Path) -> str:
    """Build a deterministic artifact identifier from a relative path."""
    digest = sha1(relative_path.as_posix().encode(), usedforsecurity=False).hexdigest()
    return f"artifact-{digest[:12]}"


def classify_artifact_kind(relative_path: Path) -> SimulationArtifactKind:
    """Classify a run artifact by its relative path and extension."""
    normalized_name = relative_path.name.casefold()
    normalized_suffix = relative_path.suffix.casefold()
    normalized_parts = {part.casefold() for part in relative_path.parts}

    if normalized_suffix in {".idf", ".epw"} or "input" in normalized_parts:
        return SimulationArtifactKind.INPUT

    if normalized_name in {"stdout.log", "stderr.log"} or normalized_suffix in {".log", ".out"}:
        return SimulationArtifactKind.LOG

    if normalized_suffix in {".err", ".audit", ".bnd", ".mdd", ".mtd"}:
        return SimulationArtifactKind.DIAGNOSTIC

    if normalized_suffix == ".sql":
        return SimulationArtifactKind.DATABASE

    if normalized_suffix in {".eso", ".mtr"}:
        return SimulationArtifactKind.TIME_SERIES

    if normalized_suffix in {".csv", ".htm", ".html"}:
        return SimulationArtifactKind.TABULAR

    if normalized_suffix == ".json":
        return SimulationArtifactKind.METADATA

    return SimulationArtifactKind.OTHER


def guess_media_type(relative_path: Path) -> str | None:
    """Guess a media type for a manifest artifact path."""
    normalized_suffix = relative_path.suffix.casefold()
    explicit_media_types = {
        ".epw": "text/plain",
        ".err": "text/plain",
        ".eso": "text/plain",
        ".idf": "text/plain",
        ".mtr": "text/plain",
        ".sql": "application/vnd.sqlite3",
    }
    if normalized_suffix in explicit_media_types:
        return explicit_media_types[normalized_suffix]

    guessed_type, _ = mimetypes.guess_type(relative_path.name)
    return guessed_type


__all__ = [
    "ArtifactManifest",
    "build_artifact_id",
    "classify_artifact_kind",
    "guess_media_type",
]
