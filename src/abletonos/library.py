"""Sample library organization for AbletonOS."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

AUDIO_EXTENSIONS: frozenset[str] = frozenset({".wav", ".aiff", ".mp3", ".flac"})

VALID_TYPES: list[str] = ["Drums", "Bass", "Synth", "FX", "Vocals", "Guitar", "Other"]

KEYWORD_MAP: dict[str, str] = {
    # Drums
    "kick": "Drums",
    "snare": "Drums",
    "hihat": "Drums",
    "hi-hat": "Drums",
    "tom": "Drums",
    "clap": "Drums",
    "cymbal": "Drums",
    "perc": "Drums",
    "drum": "Drums",
    # Bass
    "bass": "Bass",
    "sub": "Bass",
    "808": "Bass",
    # Synth
    "synth": "Synth",
    "pad": "Synth",
    "lead": "Synth",
    "arp": "Synth",
    "chord": "Synth",
    "pluck": "Synth",
    # FX
    "fx": "FX",
    "sfx": "FX",
    "riser": "FX",
    "impact": "FX",
    "sweep": "FX",
    "noise": "FX",
    "foley": "FX",
    # Vocals
    "vocal": "Vocals",
    "vox": "Vocals",
    "voice": "Vocals",
    "chant": "Vocals",
    "spoken": "Vocals",
    # Guitar
    "guitar": "Guitar",
    "strum": "Guitar",
    "pick": "Guitar",
}


@dataclass
class SampleEntry:
    """A single sample file and its proposed library destination."""

    source_path: Path
    pack_name: str
    proposed_type: str
    destination_path: Path  # relative: Type/pack-name/filename


@dataclass
class ImportResult:
    """Result of an import_samples call."""

    copied: int = 0
    skipped: int = 0
    errors: list[tuple[Path, str]] = field(default_factory=list)


def classify_sample(file: Path, source_root: Path) -> str:
    """Classify a sample into a type category.

    Priority:
    1. Parent folder name matches a known type (case-insensitive)
    2. Keyword match on stem (lowercased)
    3. Fallback: "Other"
    """
    try:
        relative = file.relative_to(source_root)
    except ValueError:
        relative = file

    # Check intermediate folders (exclude the filename itself)
    for part in relative.parts[:-1]:
        for valid_type in VALID_TYPES:
            if part.lower() == valid_type.lower():
                return valid_type

    # Keyword match on filename stem
    stem = file.stem.lower()
    for keyword, type_name in KEYWORD_MAP.items():
        if keyword in stem:
            return type_name

    return "Other"
