"""Tests for analyze_folder."""
from pathlib import Path

from abletonos.library import analyze_folder


def _make_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def test_analyze_finds_audio_files(tmp_path):
    """Finds .wav, .aiff, .mp3, .flac; skips non-audio."""
    pack = tmp_path / "My-Pack"
    pack.mkdir()
    _make_file(pack / "kick.wav")
    _make_file(pack / "snare.aiff")
    _make_file(pack / "loop.mp3")
    _make_file(pack / "pad.flac")
    _make_file(pack / "readme.txt")   # should be skipped
    _make_file(pack / "cover.png")    # should be skipped

    entries = analyze_folder(pack)
    filenames = {e.source_path.name for e in entries}

    assert filenames == {"kick.wav", "snare.aiff", "loop.mp3", "pad.flac"}


def test_analyze_pack_name_from_folder(tmp_path):
    """pack_name is derived from the source folder's name."""
    pack = tmp_path / "Splice-Drums-2024"
    pack.mkdir()
    _make_file(pack / "kick-01.wav")

    entries = analyze_folder(pack)

    assert len(entries) == 1
    assert entries[0].pack_name == "Splice-Drums-2024"


def test_analyze_destination_path_structure(tmp_path):
    """destination_path is relative: Type/pack-name/filename."""
    pack = tmp_path / "My-Pack"
    pack.mkdir()
    _make_file(pack / "kick-01.wav")

    entries = analyze_folder(pack)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.destination_path == Path("Drums") / "My-Pack" / "kick-01.wav"


def test_analyze_empty_folder(tmp_path):
    """Empty folder returns empty list."""
    pack = tmp_path / "Empty-Pack"
    pack.mkdir()

    entries = analyze_folder(pack)

    assert entries == []
