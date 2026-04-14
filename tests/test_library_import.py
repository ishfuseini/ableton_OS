"""Tests for import_samples."""

from pathlib import Path

from abletonos.library import SampleEntry, import_samples


def _make_entry(source_path: Path, pack_name: str, proposed_type: str) -> SampleEntry:
    return SampleEntry(
        source_path=source_path,
        pack_name=pack_name,
        proposed_type=proposed_type,
        destination_path=Path(proposed_type) / pack_name / source_path.name,
    )


def _make_audio_file(path: Path, content: bytes = b"RIFF") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_import_copies_files(tmp_path):
    """Files land at Type/pack-name/filename under library_root."""
    src = _make_audio_file(tmp_path / "source" / "kick-01.wav")
    library = tmp_path / "library"
    entry = _make_entry(src, "My-Pack", "Drums")

    result = import_samples([entry], library)

    dest = library / "Drums" / "My-Pack" / "kick-01.wav"
    assert dest.exists()
    assert result.copied == 1
    assert result.skipped == 0
    assert result.errors == []


def test_import_preserves_mtime(tmp_path):
    """shutil.copy2 preserves file modification time."""
    src = _make_audio_file(tmp_path / "source" / "snare.wav")
    original_mtime = src.stat().st_mtime
    library = tmp_path / "library"
    entry = _make_entry(src, "My-Pack", "Drums")

    import_samples([entry], library)

    dest = library / "Drums" / "My-Pack" / "snare.wav"
    assert abs(dest.stat().st_mtime - original_mtime) < 1.0


def test_import_skips_existing(tmp_path):
    """Does not overwrite a file that already exists at the destination."""
    src = _make_audio_file(tmp_path / "source" / "pad.wav", b"NEW")
    library = tmp_path / "library"
    dest = library / "Synth" / "My-Pack" / "pad.wav"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"ORIGINAL")

    entry = _make_entry(src, "My-Pack", "Synth")
    result = import_samples([entry], library)

    assert dest.read_bytes() == b"ORIGINAL"
    assert result.copied == 0
    assert result.skipped == 1


def test_import_creates_directories(tmp_path):
    """Creates Type/pack-name/ directory structure if it doesn't exist."""
    src = _make_audio_file(tmp_path / "source" / "vocal.wav")
    library = tmp_path / "library"
    entry = _make_entry(src, "New-Pack", "Vocals")

    import_samples([entry], library)

    assert (library / "Vocals" / "New-Pack").is_dir()
