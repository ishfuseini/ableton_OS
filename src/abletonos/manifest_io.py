"""I/O operations for manifest files with atomic writes and file locking."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import portalocker

from abletonos.manifest import Manifest

LOCK_FILE_NAME = ".manifest.lock"
MANIFEST_FILE_NAME = "manifest.json"


def get_lock_path(project_path: Path) -> Path:
    """Return the path to the lock file for a project."""
    return project_path / LOCK_FILE_NAME


def get_manifest_path(project_path: Path) -> Path:
    """Return the path to the manifest file for a project."""
    return project_path / MANIFEST_FILE_NAME


def atomic_write_manifest(manifest_path: Path, manifest_obj: Manifest) -> None:
    """Write manifest to a temporary file and atomically replace the target.

    Uses os.fsync() to ensure the temp file is flushed to disk before
    the atomic os.replace() operation.

    Args:
        manifest_path: The final path where the manifest should be written.
        manifest_obj: The Manifest model instance to write.
    """
    temp_path = manifest_path.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(
            json.loads(manifest_obj.model_dump_json()),
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, manifest_path)


@contextmanager
def manifest_lock(
    project_path: Path, timeout: float = 30.0
) -> Generator[None, None, None]:
    """Context manager for acquiring an exclusive lock on a project.

    Uses exponential backoff when lock acquisition fails, up to the specified
    timeout. Raises TimeoutError if the lock cannot be acquired within the
    timeout period.

    Args:
        project_path: Path to the project directory (lock file will be created inside).
        timeout: Maximum time to wait for lock acquisition in seconds.

    Raises:
        TimeoutError: If the lock cannot be acquired within the timeout.

    Yields:
        None when the lock is successfully acquired.
    """
    lock_path = get_lock_path(project_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    backoff = 0.1
    max_backoff = 2.0
    lock: portalocker.Lock | None = None

    while True:
        elapsed = time.monotonic() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            raise TimeoutError(
                f"Could not acquire lock {lock_path} in {timeout}s"
            )
        try:
            lock = portalocker.Lock(lock_path, timeout=min(1.0, remaining))
            lock.acquire()
            break
        except portalocker.LockException as err:
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

    try:
        yield
    finally:
        if lock is not None:
            lock.release()


def read_manifest(project_path: Path) -> Manifest | None:
    """Read and validate a manifest from a project directory.

    Args:
        project_path: Path to the project directory containing manifest.json.

    Returns:
        The validated Manifest object if the file exists, None otherwise.
    """
    manifest_path = get_manifest_path(project_path)
    if not manifest_path.exists():
        return None

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    return Manifest(**data)


def write_manifest(project_path: Path, manifest: Manifest) -> None:
    """Write manifest to a project directory with locking and version increment.

    This function:
    1. Acquires an exclusive lock on the project
    2. Reads the existing manifest to get the current manifest_version
    3. Increments the manifest_version using next_manifest_version()
    4. Writes the manifest atomically
    5. Releases the lock

    Args:
        project_path: Path to the project directory.
        manifest: The Manifest model instance to write.
    """
    manifest_path = get_manifest_path(project_path)

    with manifest_lock(project_path):
        existing = read_manifest(project_path)
        if existing is not None:
            manifest.manifest_version = existing.next_manifest_version()
        else:
            manifest.manifest_version = manifest.next_manifest_version()

        manifest.update_timestamp()
        atomic_write_manifest(manifest_path, manifest)
