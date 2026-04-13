# AbletonOS — Developer Specification

## Overview

AbletonOS is a local macOS CLI tool that keeps Ableton projects portable and sample libraries searchable. The core jobs: (1) never lose a project to broken sample references, (2) organize and search your sample library without opening Ableton, (3) understand what sounds you're gravitating toward over time.

Platform: macOS only. Single-user, local machine. No cloud, no accounts.

## Core Problem Model

**Pain 1 — Broken projects:** Ableton doesn't save samples with the project. Move to a new computer, open an old .als, and the sample references are dead.

**Pain 2 — Chaotic sample library:** Thousands of samples scattered across folders from different sources, named inconsistently, impossible to find without opening Ableton.

**Pain 3 — No visibility into creative habits:** Which sample packs do you actually use? What sounds dominate your recent work? Unknown without manual digging.

## Architecture

### Storage Model

```
~/Music/
├── Ableton/                    # Default Ableton projects root
│   └── [Year]/[Month]/[YYYY-MM-DD] ProjectName/
│       ├── README.md
│       ├── manifest.json
│       └── Samples/
├── AbletonLibrary/             # Organized sample library (Ableton Watched Folder)
│   ├── drum/
│   │   ├── kick/
│   │   ├── snare/
│   │   └── hi-hat/
│   ├── synth/
│   │   ├── pad/
│   │   └── stab/
│   ├── vocal/
│   ├── fx/
│   └── ...
└── Samples/                    # Raw unorganized source material (indexed only)
    ├── DrumBro/
    ├── old_house/
    └── Splice/

~/Library/Application Support/abltonOS/
├── config.yaml                 # User configuration
├── library.db                 # SQLite sample index
├── extensions/                # Hook scripts
└── pocketbase/                # (future) PB binary + data

~/Library/Logs/abltonOS/        # On-demand logs
```

### Config: `config.yaml`

```yaml
library_path: ~/Music/AbletonLibrary
projects_path: ~/Music/Ableton
samples_path: ~/Music/Samples
backup_path: ~/Music/AbletonBackups
backup_retention: 14
pocketbase:
  enabled: false
  port: 8090
```

## Data Model

### Sample Manifest (per sample, future)

Stored in a SQLite column, not a sidecar file (sidecars deferred to future).

```json
{
  "sample_uuid": "uuid-v4",
  "original_path": "/Users/.../old_house/kick_02.wav",
  "new_path": "~/Music/AbletonLibrary/drum/kick/kick_02.wav",
  "filename": "kick_02.wav",
  "size_bytes": 142000,
  "mtime": "2024-03-15T10:22:00Z",
  "sha256": "abc123...",
  "source": "old_house",
  "tags": {
    "instrument": "drum",
    "type": "one-shot"
  },
  "used_in": ["project_uuid_1", "project_uuid_2"]
}
```

### Project Manifest (`manifest.json`)

Canonical per-project metadata, written atomically (temp file + rename).

```json
{
  "schema_version": "1.0",
  "project_uuid": "uuid-v4",
  "project_name": "2026-04-13 My Song",
  "created_at": "2026-04-13T09:00:00Z",
  "updated_at": "2026-04-13T09:00:00Z",
  "generated_by": "abltonOS/0.1",
  "original_path": null,
  "tags": [],
  "finder_tags": [],
  "resources": [],
  "backups": [],
  "version_history": [],
  "cli_version": "0.1.0"
}
```

### Resource Object

```json
{
  "resource_uuid": "uuid-v4",
  "path": "Samples/kick.wav",
  "source_filename": "kick_02_final_v3.wav",
  "sidecar_present": false,
  "size_bytes": 142000,
  "mtime": "2024-03-15T10:22:00Z",
  "sha256_checksum": "abc123...",
  "tags": [],
  "finder_tags": [],
  "extraction_status": "none",
  "audio_metadata_summary": null
}
```

## CLI Commands

### `index-samples`

```
abletonos index-samples [--path /path/to/samples]
```

- Walks the configured or specified samples directory
- Extracts: filename, path, size, mtime, parent_folder (→ `source` tag)
- Stores in `library.db`
- Output: sample count, total size, detected packs

No tagging in MVP — source is auto-detected from parent folder. Tagging deferred to post-MVP.

### `organize`

```
abletonos organize [--target ~/Music/AbletonLibrary]
```

- Restructure samples into the organized folder by instrument/type
- Default structure: `instrument/type/filename`
- Copy (not move) for safety — originals remain in place
- Update `library.db` with new paths
- Requires `index-samples` to have been run first

Does not copy into Ableton — Ableton will access via Watched Folder.

### `browse`

```
abletonos browse
```

- Interactive CLI with drill-down: choose axis (instrument / type / source), then category, then see samples
- Show counts per category at each level
- Options per sample: Reveal in Finder, Copy path, Add to clipboard

### `collect`

```
abletonos collect path/to/project.als [--dry-run]
```

- Read external sample references from .als file (XML parsing)
- For each reference: check if sample exists in library or project Samples/
- If sample not found: report as missing
- If sample found but reference path broken: offer to relink to library copy
- Pre-op snapshot to `.snapshots/` before any writes
- `--dry-run` shows what would happen without making changes

### `new`

```
abletonos new "Project Name"
```

- Creates `projects_path/YYYY/MM/YYYY-MM-DD ProjectName/`
- Creates `README.md` and `manifest.json` template
- Opens in Finder

### `init-config`

```
abletonos init-config
```

- Interactive wizard to create `config.yaml`
- Sets paths, backup destination, PocketBase preferences

### `pb` (future)

```
abletonos pb start | stop | status
```

- Start/stop PocketBase as managed child process
- Only available when PocketBase is enabled in config

## Ableton Integration

### Watched Folder

User points Ableton's browser at `~/Music/AbletonLibrary/`. Samples are organized in subfolders by instrument/type/source. Ableton's browser shows them organized, no duplication needed.

### `.als` Collection

`collect` does not copy samples into each project's `Samples/` folder. Instead:
- Ensures all sample references in the .als point to valid paths
- If a sample lives in the library and the .als points to the old path, updates the reference
- If a sample doesn't exist anywhere, reports it as missing

This preserves portability: a project with all its samples in the library travels with a .als that references library paths.

## Backup

### Local Backup: rsync

```
abletonos backup [--dest /path/to/backup]
```

- rsync-style incremental backup with hardlink strategy
- Default destination from config, overridable per-run
- Retains last N snapshots (configurable, default 14)
- PocketBase placed in maintenance/read-only mode before snapshot

### Backup via Web UI (future)

PocketBase web UI provides a "Backup Now" button:
- Fires webhook to a Python wrapper script
- Script runs the rsync backup
- Result shown in UI

## PocketBase (future)

Single-user local deployment, disabled by default.

- Auto-downloaded on first run with PB enabled
- Starts as ephemeral child process when needed, terminates after
- Web UI on `localhost:8090`
- Collections: `projects`, `resources`, `audit`

PocketBase only needed when:
- Cross-project full-text search is desired
- Web UI for browsing is desired
- Creative insights dashboard is desired

## Atomic Writes

`manifest.json` always written atomically:
1. Write to `.{filename}.tmp`
2. `os.fsync` the temp file
3. `os.replace` to final path

This prevents corruption if the process is interrupted mid-write.

## File Locking

When multiple `abletonos` processes might run simultaneously:
- Advisory locking per project using `portalocker`
- Lock acquired before reading/writing `manifest.json`
- Lock released after write completes

## Extensions / Hooks (future)

Hooks are executable scripts in `~/Library/Application Support/abltonOS/extensions/`, disabled by default.

- Each hook has a `hooks.json` manifest
- Hooks must be on a user-managed whitelist or pass a checksum match
- Modes: `sync` (default) or `async`
- `sync` hooks: stdout/stderr shown in CLI output
- `async` hooks: fire and return, no output shown

## Implementation Phases

### Phase 1 — Foundation
- Project scaffold, CLI skeleton, `init-config`
- `config.yaml` read/write

### Phase 2 — Sample Indexing
- `index-samples` walking directory tree
- SQLite library.db creation and query

### Phase 3 — Browse
- `browse` interactive drill-down CLI
- SQLite → interactive output

### Phase 4 — Organize
- `organize` restructure (copy mode)
- New folder layout creation
- Update library.db with new paths

### Phase 5 — Project Collect
- `collect` .als XML parsing
- Reference resolution against library
- Pre-op snapshot

### Phase 6 — Project Creation
- `new` command
- README + manifest template

### Phase 7 — Backup
- `backup` rsync wrapper
- Retention management

### Phase 8 — PocketBase (future)
- PB download + start/stop
- PB collections sync
- Web UI

## Out of Scope (MVP)

- Deduplication of identical samples
- Audio metadata/BPM extraction
- Finder tags automation
- Plugin/preset setup
- Windows support
- Multi-user/PocketBase auth

## Open Questions

1. **Copy vs move for organize:** Default to copy (safe). Move available as an opt-in flag.
2. **PocketBase timing:** Ship without it. Add when user asks for cross-project search or web UI.
3. **Tagging UX:** MVP auto-tags from folder structure. Manual tagging in post-MVP.
