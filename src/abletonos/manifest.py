"""Pydantic models for the AbletonOS project manifest."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Resource(BaseModel):
    """A resource file (sample, audio file, etc.) tracked in the manifest."""

    resource_uuid: UUID = Field(default_factory=uuid4)
    path: str
    source_filename: str
    sidecar_present: bool = False
    size_bytes: int = Field(ge=0)
    mtime: datetime
    sha256_checksum: str = Field(min_length=64, max_length=64)
    tags: list[str] = Field(default_factory=list)
    finder_tags: list[str] = Field(default_factory=list)
    extraction_status: str = Field(default="none")
    audio_metadata_summary: dict | None = None


class VersionHistoryEntry(BaseModel):
    """An entry in the version history for an .als file."""

    als_filename: str
    version_number: int
    created_at: datetime
    note: str = ""


class Manifest(BaseModel):
    """The AbletonOS project manifest model.

    This is the canonical manifest stored as manifest.json in each project.
    It includes all project metadata, resource tracking, and version history.
    """

    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    project_uuid: UUID
    project_name: str
    created_at: datetime
    updated_at: datetime
    generated_by: str
    original_path: str | None = None
    project_root: str | None = None
    tags: list[str] = Field(default_factory=list)
    finder_tags: list[str] = Field(default_factory=list)
    manifest_version: int = Field(ge=0, default=0)
    resources: list[Resource] = Field(default_factory=list)
    backups: list[dict] = Field(default_factory=list)
    version_history: list[VersionHistoryEntry] = Field(default_factory=list)
    cli_version: str

    def next_manifest_version(self) -> int:
        """Return the next manifest version number.

        Call this before writing to increment the version.
        """
        return self.manifest_version + 1

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to now."""
        self.updated_at = datetime.utcnow()
