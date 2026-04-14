"""Tests for manifest I/O operations including atomic writes and file locking."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from abletonos.manifest import Manifest
from abletonos.manifest_io import (
    atomic_write_manifest,
    get_lock_path,
    get_manifest_path,
    manifest_lock,
    read_manifest,
    write_manifest,
)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def sample_manifest() -> Manifest:
    """Create a sample manifest for testing."""
    return Manifest(
        schema_version="1.0.0",
        project_uuid=uuid4(),
        project_name="Test Project",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        generated_by="test",
        cli_version="0.1.0",
        manifest_version=0,
    )


class TestAtomicWriteManifest:
    """Tests for atomic_write_manifest function."""

    def test_atomic_write_manifest(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify temp file is used and renamed correctly."""
        manifest_path = temp_project / "manifest.json"

        atomic_write_manifest(manifest_path, sample_manifest)

        assert manifest_path.exists()
        assert not manifest_path.with_suffix(".json.tmp").exists()

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["project_name"] == "Test Project"
        assert data["schema_version"] == "1.0.0"

    def test_atomic_write_overwrites_existing(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify overwriting an existing manifest works correctly."""
        manifest_path = temp_project / "manifest.json"

        atomic_write_manifest(manifest_path, sample_manifest)

        sample_manifest.project_name = "Updated Project"
        sample_manifest.manifest_version = 1

        atomic_write_manifest(manifest_path, sample_manifest)

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["project_name"] == "Updated Project"
        assert data["manifest_version"] == 1


class TestLockAcquisition:
    """Tests for lock acquisition functionality."""

    def test_lock_creates_lock_file(self, temp_project: Path) -> None:
        """Verify lock file is created when acquiring lock."""
        lock_path = get_lock_path(temp_project)

        with manifest_lock(temp_project):
            assert lock_path.exists()

    def test_lock_released_after_context(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify lock is released after context manager exits."""
        lock_path = get_lock_path(temp_project)

        with manifest_lock(temp_project):
            pass

        with open(lock_path, "rb") as _:
            pass

    def test_concurrent_lock_rejected(self, temp_project: Path) -> None:
        """Verify second lock acquisition fails while first is held."""
        concurrent_acquired = threading.Event()
        first_acquired = threading.Event()
        second_rejected = threading.Event()
        barrier = threading.Barrier(2)
        lock_holder: dict[str, threading.Thread] = {}

        def hold_lock() -> None:
            barrier.wait()
            try:
                with manifest_lock(temp_project, timeout=30.0):
                    first_acquired.set()
                    concurrent_acquired.wait()
            finally:
                lock_holder.pop("holder", None)

        def try_lock_short() -> None:
            barrier.wait()
            first_acquired.wait()
            try:
                with manifest_lock(temp_project, timeout=0.3):
                    lock_holder["second"] = threading.current_thread()
                    concurrent_acquired.set()
            except TimeoutError:
                second_rejected.set()
                concurrent_acquired.set()

        t1 = threading.Thread(target=hold_lock)
        t2 = threading.Thread(target=try_lock_short)

        t1.start()
        t2.start()

        t1.join(timeout=2)
        t2.join(timeout=2)

        assert first_acquired.is_set()
        assert second_rejected.is_set()


class TestConcurrentWriteSerialization:
    """Tests for concurrent write serialization."""

    def test_concurrent_writes_serialize(self, temp_project: Path) -> None:
        """Use threading to simulate concurrent writes, verify they serialize."""
        results: list[int] = []
        results_lock = threading.Lock()
        barrier = threading.Barrier(5)

        def write_with_version(version: int) -> None:
            barrier.wait()
            manifest = Manifest(
                schema_version="1.0.0",
                project_uuid=uuid4(),
                project_name=f"Project {version}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                generated_by="test",
                cli_version="0.1.0",
                manifest_version=0,
            )
            write_manifest(temp_project, manifest)
            with results_lock:
                results.append(version)

        threads = [
            threading.Thread(target=write_with_version, args=(i,)) for i in range(5)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        final_manifest = read_manifest(temp_project)
        assert final_manifest is not None

        manifest_path = get_manifest_path(temp_project)
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["manifest_version"] == 5


class TestReadManifest:
    """Tests for read_manifest function."""

    def test_read_manifest_returns_none_if_not_exists(self, temp_project: Path) -> None:
        """Verify read_manifest returns None when file doesn't exist."""
        result = read_manifest(temp_project)
        assert result is None

    def test_read_manifest_returns_manifest(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify read_manifest correctly reads and validates manifest."""
        manifest_path = temp_project / "manifest.json"

        atomic_write_manifest(manifest_path, sample_manifest)

        result = read_manifest(temp_project)

        assert result is not None
        assert result.project_name == "Test Project"
        assert result.schema_version == "1.0.0"


class TestWriteManifest:
    """Tests for write_manifest function."""

    def test_write_manifest_increments_version(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify write_manifest correctly increments manifest_version."""
        write_manifest(temp_project, sample_manifest)

        result = read_manifest(temp_project)
        assert result is not None
        assert result.manifest_version == 1

    def test_write_manifest_preserves_other_fields(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify write_manifest preserves other manifest fields."""
        write_manifest(temp_project, sample_manifest)

        result = read_manifest(temp_project)
        assert result is not None
        assert result.project_name == "Test Project"
        assert result.project_uuid == sample_manifest.project_uuid
        assert result.schema_version == "1.0.0"

    def test_write_manifest_multiple_writes_increment(
        self, temp_project: Path, sample_manifest: Manifest
    ) -> None:
        """Verify multiple writes correctly increment version each time."""
        for _ in range(1, 4):
            write_manifest(temp_project, sample_manifest)

        result = read_manifest(temp_project)
        assert result is not None
        assert result.manifest_version == 3
