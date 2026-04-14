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


def analyze_folder(source: Path) -> list[SampleEntry]:
    """Walk source folder and classify all audio files.

    Returns a list of SampleEntry objects with proposed destinations.
    Returns empty list if no audio files are found.
    """
    pack_name = source.name
    entries: list[SampleEntry] = []

    for file in sorted(source.rglob("*")):
        if not file.is_file():
            continue
        if file.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        proposed_type = classify_sample(file, source)
        entries.append(
            SampleEntry(
                source_path=file,
                pack_name=pack_name,
                proposed_type=proposed_type,
                destination_path=Path(proposed_type) / pack_name / file.name,
            )
        )

    return entries


def import_samples(entries: list[SampleEntry], library_root: Path) -> ImportResult:
    """Copy sample entries into the library.

    Uses shutil.copy2 to preserve mtime. Skips files that already exist
    at the destination. Continues on permission errors, recording them.

    Args:
        entries: List of SampleEntry objects (from analyze_folder or preview).
        library_root: Root of the organized sample library.

    Returns:
        ImportResult with counts of copied, skipped, and errored files.
    """
    result = ImportResult()

    for entry in entries:
        dest = library_root / entry.destination_path

        if dest.exists():
            result.skipped += 1
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.source_path, dest)
            result.copied += 1
        except Exception as exc:
            result.errors.append((entry.source_path, str(exc)))

    return result


def preview(
    entries: list[SampleEntry],
    library_root: Path,
    *,
    console: object | None = None,
) -> list[SampleEntry]:
    """Render a Rich preview table and allow per-entry type overrides.

    Prints a summary of proposed classifications. If the user opts to
    override, loops through entries and prompts for a new type for each.

    Args:
        entries: List of SampleEntry objects from analyze_folder.
        library_root: Used to display full destination paths.
        console: Rich Console instance (creates one if not provided).

    Returns:
        The (possibly modified) list of SampleEntry objects.
    """
    from collections import Counter

    from rich.console import Console as RichConsole
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

    con: RichConsole = console or RichConsole()  # type: ignore[assignment]

    # Summary by type
    counts = Counter(e.proposed_type for e in entries)
    con.print(f"\n[bold]Found {len(entries)} samples[/bold]")
    for type_name in VALID_TYPES:
        if counts[type_name]:
            con.print(f"  {type_name:<10} → {counts[type_name]} files")

    # Full table
    table = Table(title="Proposed Import", show_lines=False)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Destination", style="dim")
    for entry in entries:
        dest = str(library_root / entry.destination_path)
        table.add_row(entry.source_path.name, entry.proposed_type, dest)
    con.print(table)

    if not Confirm.ask("\nOverride any classifications?", default=False, console=con):
        return entries

    updated: list[SampleEntry] = []
    type_choices = "/".join(VALID_TYPES)
    for entry in entries:
        new_type = Prompt.ask(
            f"  [cyan]{entry.source_path.name}[/cyan] (current: {entry.proposed_type})\n"
            f"  Type [{type_choices}]",
            choices=VALID_TYPES,
            default=entry.proposed_type,
            console=con,
        )
        updated.append(
            SampleEntry(
                source_path=entry.source_path,
                pack_name=entry.pack_name,
                proposed_type=new_type,
                destination_path=Path(new_type) / entry.pack_name / entry.source_path.name,
            )
        )

    return updated
