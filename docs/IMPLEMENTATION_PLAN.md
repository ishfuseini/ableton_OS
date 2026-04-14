# AbletonOS — Phased Implementation Plan

Based on: `ONE_PAGER.md`, `DEV_SPEC.md`, `SPEC.md`

---

## Phase 0 — Project Scaffold ✅

**Duration:** 1–2 days
**Goal:** Ready-to-run CLI skeleton with packaging and logging.
**Status:** COMPLETED — Merged via PR #1

### Tasks

- [x] Initialize Python project with `pyproject.toml` (package name: `abletonos`)
- [x] Set up Typer CLI entrypoint (`abletonos` command)
- [x] Define XDG-style path constants:
  - Config: `~/.abletonOS/config/`
  - Data: `~/.abletonOS/db/`
  - Logs: `~/.abletonOS/logs/`
  - Templates: `~/.abletonOS/templates/`
- [x] Configure Python `logging` module (INFO default, DEBUG via `--debug` flag)
- [x] Add dependencies to `pyproject.toml`:
  - `typer >= 0.6`
  - `rich` (for interactive UI)
  - `portalocker >= 2.7`
  - `requests >= 2.28`
  - `pydantic >= 1.10`
  - `pytest`
  - `packaging.version`
- [x] Create stub `__main__.py` and CLI group structure
- [x] Initialize git repo (if not already)

### Exit Criteria

- [x] `python -m abletonos --help` prints CLI help
- [x] Config dir structure created on first run

---

## Phase 1 — Config & PocketBase Bootstrap

**Duration:** 2–4 days
**Goal:** `init-config` wizard creates `config.yaml` with hosted PocketBase.

**Status:** COMPLETED (Core functionality - hosted PB, not embedded)

### Tasks

- [x] Implement `init-config` interactive wizard:
  - Prompt for project root path (e.g., `~/Music/Ableton`)
  - Prompt for PocketBase URL (hosted instance)
  - Create default directory structure under `~/.abletonOS/`
- [x] Implement `config.yaml` read/write module (atomic writes)
- [x] Implement `pb` command:
  - `pb` — health-check via HTTP to hosted PB
- [x] Update implementation plan to reflect hosted PB approach

### Exit Criteria

- [x] `abletonos init-config` creates `~/.abletonOS/config/config.yaml`
- [x] `abletonos pb` confirms connection to hosted PB
- [x] Config stores: project_root, pocketbase_url

### Note on PocketBase Hosting

PocketBase is **hosted externally** (not embedded in CLI). Users self-host PB and provide the URL during `init-config`. This simplifies the CLI significantly.

---

## Phase 2 — Manifest API & Atomic Write + Locking

**Duration:** 2–3 days
**Goal:** Reliable manifest read/write with schema validation, atomicity, and concurrency safety.
**Status:** COMPLETED — Merged via PR #3

### Tasks

- [ ] Define manifest JSON Schema (`schema.json`) per DEV_SPEC
  - Include all required fields: `schema_version`, `project_uuid`, `project_name`, `created_at`, `updated_at`, `generated_by`, `resources`, `version_history`, `cli_version`
  - Include resource object schema with `resource_uuid`, `path`, `source_filename`, `size_bytes`, `mtime`, `sha256_checksum`
- [ ] Implement manifest model (Pydantic dataclass or `dataclass + jsonschema`)
- [ ] Implement atomic write helper:
  ```
  1. Write to .manifest.json.tmp
  2. os.fsync() temp file
  3. os.replace() to final path
  ```
- [ ] Implement file locking with `portalocker`:
  - Per-project lock: `<project>/.manifest.lock`
  - Default timeout: 30s with exponential backoff
- [ ] Add `manifest_version` integer field (increment on every write)
- [ ] Unit tests:
  - `test_manifest_atomic_write` — simulate interruption, confirm no partial writes
  - `test_file_locking` — concurrent write serialization

### Exit Criteria

- Manifest writes are atomic (crash-safe)
- Concurrent CLI invocations on same project serialize correctly
- Schema validation on read and write

---

## Phase 3 — Sample Library Organization ✅

**Duration:** 3 days
**Goal:** `add-samples` command organizes downloaded samples into a typed library.
**Status:** COMPLETED — Merged via PR #4

### Tasks

- [x] Add `library_root` field to `AbletonOSConfig` (config module)
- [x] Update `init-config` wizard to prompt for `--library-root`
- [x] Implement `src/abletonos/library.py`:
  - `classify_sample()` — folder-name keywords → filename keywords → "Other"
  - `analyze_folder()` — recursively find audio files, classify, build `SampleEntry` list
  - `preview()` — show grouped table, allow per-type overrides via Rich prompt
  - `import_samples()` — copy to `<library_root>/Type/<pack-name>/` using `shutil.copy2`
- [x] Implement `add-samples <folder>` CLI command (analyze → preview → import)
- [x] Disk space check before copy
- [x] Unit tests for classify, analyze, import, preview (mock Rich prompts)

### Exit Criteria

- [x] `abletonos add-samples <folder>` copies files to `<library_root>/Type/<pack-name>/`
- [x] Classification uses folder name first, filename second, "Other" fallback
- [x] User can override type per category during preview step
- [x] Skips existing files, reports errors without aborting

### Library Structure

```
<library_root>/
  Drums/<pack-name>/*.wav
  Bass/<pack-name>/*.wav
  Synth/ | FX/ | Vocals/ | Guitar/ | Other/
```

---

## Phase 4 — Project Add

**Duration:** 2–3 days
**Goal:** `add <source>` registers an existing Ableton project into the managed project root with a manifest.

### Tasks

- [ ] Implement `add <source>` CLI command:
  - Accept path to an existing Ableton project folder
  - Derive project name from source folder name
  - Auto-generate date prefix: `YYYY-MM-DD`
  - Copy folder to `<project_root>/YYYY-MM-DD-<ProjectName>/` using `shutil.copytree`
  - Preserve all file metadata (`shutil.copy2`)
- [ ] Generate `manifest.json` in the destination project folder:
  - `project_uuid` (UUID v4)
  - `project_name` (derived from source folder name)
  - `created_at` / `updated_at` (ISO 8601)
  - `generated_by`: `abletonos/<version>`
  - `original_path`: absolute path of the source folder
  - `resources`: list of all files found (path, size_bytes, mtime, sha256_checksum)
  - `version_history`: `[]`
- [ ] SHA-256 checksum for every file in the project
- [ ] Disk space check before copy
- [ ] Handle name collisions: if target folder exists, append `-2`, `-3`, etc.
- [ ] Unit tests:
  - `test_add_creates_dated_folder` — correct `YYYY-MM-DD-Name` structure
  - `test_add_generates_manifest` — manifest fields populated correctly
  - `test_add_collision_handling` — suffix increment on collision
  - `test_add_disk_space_check` — abort when insufficient space

### Exit Criteria

- `abletonos add /path/to/MyProject` copies to `<project_root>/YYYY-MM-DD-MyProject/`
- `manifest.json` generated with all files checksummed
- Name collisions handled gracefully

---

## Phase 5 — .als Versioning

**Duration:** 2–3 days
**Goal:** `version` command increments .als file with snapshot and manifest update.

### Tasks

- [ ] Detect latest `*_vN.als` file in project (parse filename)
- [ ] Create copy: `_vN.als` → `_vN+1.als`
- [ ] Snapshot previous `.als` into `.snapshots/` before overwrite
- [ ] Update `manifest.version_history`:
  - `als_filename`, `version_number`, `created_at`, `note`
- [ ] Increment `manifest_version`, update `updated_at`
- [ ] Atomic manifest write
- [ ] Sync project update to PocketBase

### Exit Criteria

- `abletonos version --als-file "My Song_v1.als"` creates `My Song_v2.als`
- Snapshot of previous .als exists in `.snapshots/`
- `version_history` array in manifest grows with new entry

---

## Phase 6 — Archive Export & Search

**Duration:** 2–4 days
**Goal:** `export-archive` creates portable ZIP; `search` enables PB-backed discovery.

### Tasks

#### `export-archive`

- [ ] Create ZIP with structure:
  ```
  <project_name>/
    README.md
    manifest.json
    Samples/
      [pack-slug]/
        *.wav
    *.als
  ```
- [ ] Use atomic zip creation (temp + rename)
- [ ] Include all sample files and .als files
- [ ] `--dest PATH` override for output location

#### `index` / `reindex`

- [ ] Scan configured project root recursively for `manifest.json`
- [ ] Upsert project docs to PB for each found manifest
- [ ] Upsert resource docs per manifest.resources
- [ ] Write audit event for reindex operation

#### `search`

- [ ] Interactive wizard with faceted filters:
  - Project name (FTS)
  - Tags
  - Date range
  - Resource filename / pack-slug
- [ ] Paginated results with actions:
  - Reveal in Finder
  - Show metadata
  - Export

### Exit Criteria

- `export-archive` produces valid ZIP that rehydrates on another machine
- `index` syncs all projects and resources to PB
- `search` returns relevant results via PB FTS

---

## Phase 7 — Audit & Diagnostics

**Duration:** 2 days
**Goal:** Structured audit trail and troubleshooting command.

### Tasks

- [ ] Write audit events to PB `audit` collection on every CLI operation:
  - `event_type`: `project.create`, `samples.add`, `version.bump`, `export.archive`, etc.
  - `timestamp`, `project_uuid`, `payload` (structured JSON)
- [ ] Write local fallback audit log: `~/.abletonOS/db/audit-local.jsonl`
- [ ] Implement `diagnose` command:
  - Check PB status and connectivity
  - Report disk free space
  - Validate `config.yaml`
  - List pending sync tasks
  - Collect recent logs into tarball for debugging

### Exit Criteria

- Audit events queryable via PB admin UI
- `abletonos diagnose` produces actionable debug report

---

## Phase 8 — Polish, Tests & Documentation

**Duration:** 2–4 days
**Goal:** Production-ready MVP with tests, docs, and acceptance criteria met.

### Tasks

- [ ] Add unit tests for core modules:
  - `test_manifest_atomic_write`
  - `test_checksum_sha256` (including zero-length file)
  - `test_file_locking` (concurrent threads/processes)
  - `test_version_command` (vN → vN+1 naming)
  - `test_export_archive` (ZIP contents and manifest match)
  - `test_pb_start_stop_helpers`
- [ ] Manual acceptance testing:
  - [ ] `init-config` → config created, PB downloaded and started
  - [ ] `new` → folder created with README and valid manifest
  - [ ] `add-samples` → files in `Samples/[pack-slug]` and manifest updated
  - [ ] `version` → new .als created, snapshot created, `version_history` updated
  - [ ] `export-archive` → ZIP contains manifest and assets
  - [ ] PB search → projects & resources appear in PB UI; audit records created
  - [ ] Snapshot retention → prune removes snapshots > 30 days old
- [ ] Write README.md with:
  - Installation instructions
  - First-run guide (`init-config`, `pb start`)
  - Command reference
  - Project structure documentation
- [ ] Add example `config.yaml` to docs

### Exit Criteria

- All unit tests pass
- All acceptance criteria verified manually
- README complete and runnable by a new user

---

## Timeline Summary

| Phase | Name | Duration | Cumulative |
|-------|------|----------|------------|
| 0 | Project Scaffold | 1–2 days | 1–2 days |
| 1 | Config & PB Bootstrap | 2–4 days | 3–6 days |
| 2 | Manifest API & Locking | 2–3 days | 5–9 days |
| 3 | Sample Library Organization ✅ | 3 days | 8–11 days |
| 4 | Project Add | 2–3 days | 10–14 days |
| 5 | .als Versioning | 2–3 days | 13–22 days |
| 6 | Archive Export & Search | 2–4 days | 15–26 days |
| 7 | Audit & Diagnostics | 2 days | 17–28 days |
| 8 | Polish, Tests & Docs | 2–4 days | 19–32 days |

**Estimated total: 3–5 weeks** for a single engineer (assuming familiarity with PocketBase and no blocking dependencies).

---

## Dependency Graph

```
Phase 0 ──► Phase 1 ──► Phase 2 ──┬──► Phase 3 ──► Phase 4 ──► Phase 5 ──┬──► Phase 6 ──► Phase 7 ──► Phase 8
                                  │                    │                    │
                                  │                    └────────────────────┴───► (parallel tracks)
                                  │
                                  └──────────────────────────────────────────────► (PB needed for 6, 7)

Note: Phase 3 (new/import) and Phase 4 (add-samples) are independent after Phase 2.
Phase 5 (version) depends on Phase 3.
Phase 6 (search) and Phase 7 (audit) both need PB and can run in parallel after Phase 4.
```

---

## Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PocketBase binary download/verification | PB won't start | Phase 1 focuses on PB lifecycle; add retry with clear error messages |
| Manifest corruption on crash | Data loss | Phase 2 implements atomic writes first; always write to temp then rename |
| Concurrent CLI invocations | Manifest race condition | Phase 2 implements file locking before any manifest operation |
| Large sample import (multi-GB) | Disk full or hang | Check disk space before copy; use chunked copy with progress reporting |
| PB sync failures | Index drift | Queue failed syncs to `pending_sync.json`; provide `sync-pending` command |

---

## Out-of-Scope (MVP)

These are intentionally deferred to post-MVP:

- rsync backup engine & launchd integration
- Extensions/hooks system
- Binary checksum verification for PB download
- Deduplication of identical samples
- Audio metadata/BPM extraction
- Finder tags automation
- Plugin/preset setup
- Windows support
- Multi-user / PB auth (beyond single admin)
