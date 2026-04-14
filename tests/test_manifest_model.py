"""Tests for the manifest model."""

from __future__ import annotations

import json

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from abletonos.manifest import Manifest, Resource, VersionHistoryEntry


class TestResource:
    """Tests for the Resource model."""

    def test_create_resource(self) -> None:
        """Test creating a resource with required fields."""
        now = datetime.now(UTC)
        resource = Resource(
            resource_uuid=uuid4(),
            path="Samples/my-pack/kick.wav",
            source_filename="kick.wav",
            size_bytes=12345,
            mtime=now,
            sha256_checksum="a" * 64,
        )
        assert resource.path == "Samples/my-pack/kick.wav"
        assert resource.sidecar_present is False
        assert resource.extraction_status == "none"

    def test_resource_uuid_auto_generated(self) -> None:
        """Test that resource_uuid is auto-generated if not provided."""
        now = datetime.now(UTC)
        resource = Resource(
            path="Samples/test.wav",
            source_filename="test.wav",
            size_bytes=100,
            mtime=now,
            sha256_checksum="b" * 64,
        )
        assert resource.resource_uuid is not None


class TestVersionHistoryEntry:
    """Tests for the VersionHistoryEntry model."""

    def test_create_entry(self) -> None:
        """Test creating a version history entry."""
        now = datetime.now(UTC)
        entry = VersionHistoryEntry(
            als_filename="My Song_v1.als",
            version_number=1,
            created_at=now,
            note="Initial create",
        )
        assert entry.version_number == 1
        assert entry.note == "Initial create"


class TestManifest:
    """Tests for the Manifest model."""

    def test_create_manifest(self) -> None:
        """Test creating a manifest with required fields."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="abletonos-cli v0.1.0",
            cli_version="0.1.0",
        )
        assert manifest.schema_version == "1.0.0"
        assert manifest.manifest_version == 0
        assert len(manifest.resources) == 0

    def test_next_manifest_version(self) -> None:
        """Test incrementing manifest version."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="test",
            cli_version="0.1.0",
            manifest_version=5,
        )
        assert manifest.next_manifest_version() == 6

    def test_update_timestamp(self) -> None:
        """Test updating the timestamp."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="test",
            cli_version="0.1.0",
        )
        original_updated = manifest.updated_at
        manifest.update_timestamp()
        assert manifest.updated_at >= original_updated

    def test_add_resource(self) -> None:
        """Test adding a resource to the manifest."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="test",
            cli_version="0.1.0",
        )
        resource = Resource(
            path="Samples/test.wav",
            source_filename="test.wav",
            size_bytes=100,
            mtime=now,
            sha256_checksum="c" * 64,
        )
        manifest.resources.append(resource)
        assert len(manifest.resources) == 1

    def test_add_version_history(self) -> None:
        """Test adding a version history entry."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="test",
            cli_version="0.1.0",
        )
        entry = VersionHistoryEntry(
            als_filename="Test_v1.als",
            version_number=1,
            created_at=now,
            note="Initial",
        )
        manifest.version_history.append(entry)
        assert len(manifest.version_history) == 1


class TestManifestRoundTrip:
    """Tests for manifest JSON round-trip serialization."""

    def test_manifest_to_json(self) -> None:
        """Test serializing a manifest to JSON."""
        now = datetime.now(UTC)
        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=uuid4(),
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="abletonos-cli v0.1.0",
            cli_version="0.1.0",
        )
        json_str = manifest.model_dump_json(indent=2)
        data = json.loads(json_str)
        assert data["schema_version"] == "1.0.0"
        assert data["manifest_version"] == 0

    def test_manifest_from_json(self) -> None:
        """Test deserializing a manifest from JSON."""
        project_uuid = str(uuid4())
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        json_str = json.dumps({
            "schema_version": "1.0.0",
            "project_uuid": project_uuid,
            "project_name": "Test Project",
            "created_at": now,
            "updated_at": now,
            "generated_by": "abletonos-cli v0.1.0",
            "cli_version": "0.1.0",
            "manifest_version": 1,
            "resources": [],
            "version_history": [],
        })
        manifest = Manifest.model_validate_json(json_str)
        assert manifest.schema_version == "1.0.0"
        assert manifest.project_name == "Test Project"
        assert manifest.manifest_version == 1

    def test_roundtrip_with_resources(self) -> None:
        """Test round-trip with resources and version history."""
        project_uuid = uuid4()
        now = datetime.now(UTC)
        resource_uuid = uuid4()

        manifest = Manifest(
            schema_version="1.0.0",
            project_uuid=project_uuid,
            project_name="Test Project",
            created_at=now,
            updated_at=now,
            generated_by="test",
            cli_version="0.1.0",
            manifest_version=1,
            resources=[
                Resource(
                    resource_uuid=resource_uuid,
                    path="Samples/test.wav",
                    source_filename="test.wav",
                    size_bytes=12345,
                    mtime=now,
                    sha256_checksum="a" * 64,
                )
            ],
            version_history=[
                VersionHistoryEntry(
                    als_filename="Test_v1.als",
                    version_number=1,
                    created_at=now,
                    note="Initial",
                )
            ],
        )

        # Serialize and deserialize
        json_str = manifest.model_dump_json(indent=2)
        restored = Manifest.model_validate_json(json_str)

        assert len(restored.resources) == 1
        assert restored.resources[0].path == "Samples/test.wav"
        assert len(restored.version_history) == 1
        assert restored.version_history[0].als_filename == "Test_v1.als"
        assert restored.manifest_version == 1