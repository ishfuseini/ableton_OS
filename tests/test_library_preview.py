"""Tests for the preview function."""

from pathlib import Path
from unittest.mock import patch

from abletonos.library import SampleEntry, preview


def _make_entry(tmp_path: Path, filename: str, proposed_type: str) -> SampleEntry:
    source = tmp_path / filename
    source.touch()
    return SampleEntry(
        source_path=source,
        pack_name="My-Pack",
        proposed_type=proposed_type,
        destination_path=Path(proposed_type) / "My-Pack" / filename,
    )


def test_preview_returns_entries_unchanged_when_no_override(tmp_path):
    """When user declines override, entries are returned unchanged."""
    entries = [_make_entry(tmp_path, "kick.wav", "Drums")]
    library_root = tmp_path / "library"

    with patch("rich.prompt.Confirm.ask", return_value=False):
        result = preview(entries, library_root)

    assert result == entries


def test_preview_override_updates_type_and_destination(tmp_path):
    """When user overrides, SampleEntry gets new type and destination_path."""
    entries = [_make_entry(tmp_path, "mystery.wav", "Other")]
    library_root = tmp_path / "library"

    with (
        patch("rich.prompt.Confirm.ask", return_value=True),
        patch("rich.prompt.Prompt.ask", return_value="Drums"),
    ):
        result = preview(entries, library_root)

    assert len(result) == 1
    assert result[0].proposed_type == "Drums"
    assert result[0].destination_path == Path("Drums") / "My-Pack" / "mystery.wav"


def test_preview_override_preserves_unchanged_entries(tmp_path):
    """Override loop processes all entries; unchanged type stays the same."""
    entries = [
        _make_entry(tmp_path, "kick.wav", "Drums"),
        _make_entry(tmp_path, "mystery.wav", "Other"),
    ]
    library_root = tmp_path / "library"

    # User answers "Drums" for kick (same), "FX" for mystery (changed)
    with (
        patch("rich.prompt.Confirm.ask", return_value=True),
        patch("rich.prompt.Prompt.ask", side_effect=["Drums", "FX"]),
    ):
        result = preview(entries, library_root)

    assert result[0].proposed_type == "Drums"
    assert result[0].destination_path == Path("Drums") / "My-Pack" / "kick.wav"
    assert result[1].proposed_type == "FX"
    assert result[1].destination_path == Path("FX") / "My-Pack" / "mystery.wav"
