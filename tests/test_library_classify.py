"""Tests for sample classification logic."""
from pathlib import Path

import pytest

from abletonos.library import classify_sample, KEYWORD_MAP, VALID_TYPES


@pytest.fixture
def source_root(tmp_path):
    return tmp_path / "My-Pack"


def test_classify_by_folder_name(tmp_path):
    """File inside a Drums/ subfolder → Drums regardless of filename."""
    source_root = tmp_path / "My-Pack"
    source_root.mkdir()
    drums_dir = source_root / "Drums"
    drums_dir.mkdir()
    file = drums_dir / "pad-01.wav"  # 'pad' would normally → Synth
    file.touch()

    result = classify_sample(file, source_root)
    assert result == "Drums"


def test_classify_by_keyword(tmp_path):
    """No folder structure — 'kick' in filename → Drums."""
    source_root = tmp_path / "My-Pack"
    source_root.mkdir()
    file = source_root / "kick-01.wav"
    file.touch()

    result = classify_sample(file, source_root)
    assert result == "Drums"


def test_classify_folder_takes_priority(tmp_path):
    """File in Drums/ folder with 'synth' in name → Drums wins."""
    source_root = tmp_path / "My-Pack"
    source_root.mkdir()
    drums_dir = source_root / "Drums"
    drums_dir.mkdir()
    file = drums_dir / "synth-kick.wav"
    file.touch()

    result = classify_sample(file, source_root)
    assert result == "Drums"


def test_classify_fallback_to_other(tmp_path):
    """Unrecognized name, no matching folder → Other."""
    source_root = tmp_path / "My-Pack"
    source_root.mkdir()
    file = source_root / "mystery-loop-01.wav"
    file.touch()

    result = classify_sample(file, source_root)
    assert result == "Other"


def test_all_type_keywords_map():
    """Every value in KEYWORD_MAP must be a valid type."""
    for keyword, type_name in KEYWORD_MAP.items():
        assert type_name in VALID_TYPES, f"Keyword '{keyword}' maps to unknown type '{type_name}'"
