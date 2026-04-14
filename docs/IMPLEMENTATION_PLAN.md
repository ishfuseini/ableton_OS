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
**Goal:** `init-config` wizard creates `config.yaml` and auto-downloads PocketBase.

### Tasks

- [ ] Implement `init-config` interactive wizard:
  - Prompt for project root path (e.g., `~/Music/Ableton`)
  - Prompt for PocketBase admin password (use once, never persist)
  - Create default directory structure under `~/.abletonOS/`
- [ ] Implement `config.yaml` read/write module
- [ ] Add PocketBase binary downloader:
  - Fetch latest macOS arm64 release from GitHub
  - Store in `~/.abletonOS/db/pocketbase/<version>/pocketbase`
  - Record version in config for reproducibility
- [ ] Implement `pb` subcommands:
  - `pb start` — launch PB as persistent child process, write PID file
  - `pb stop` — read PID and terminate PB
  - `pb status` — health-check via HTTP or PID check
- [ ] Implement PB admin creation via REST API on first run
- [ ] Stream PB logs to `~/.abletonOS/logs/pocketbase.log`

### Exit Criteria

- `abletonos init-config` creates `~/.abletonOS/config/config.yaml`
- `abletonos pb start` downloads PB (if missing) and starts PB process
- PB admin UI accessible at `http://127.0.0.1:8090`

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

## Phase 3 — Project Creation & Import

**Duration:** 3–5 days
**Goal:** `new` wizard creates date-first project folders; `import` standardizes existing projects.

### Tasks

#### `new` command

- [ ] Interactive wizard: prompt for project name
- [ ] Auto-generate date prefix: `YYYY-MM-DD`
- [ ] Create folder structure:
  ```
  <PROJECT_ROOT>/YYYY/MM/YYYY-MM-DD ProjectName/
    README.md
    manifest.json
    Samples/
  ```
- [ ] Generate `README.md` from template
- [ ] Generate `manifest.json` with:
  - `project_uuid` (UUID v4)
  - `project_name`
  - `created_at` / `updated_at`
  - `generated_by`: `abletonos/<version>`
  - `resources`: `[]`
  - `version_history`: `[]`
- [ ] Open new project in Finder

#### `import` command

- [ ] Accept `--source PATH` to existing project
- [ ] Analyze source structure: locate `.als` files, existing Samples/
- [ ] Plan target folder under configured project root
- [ ] Preview step: show copy/move operations before executing
- [ ] Default to copy (not move) for safety
- [ ] Handle name collisions with suffix increment or user prompt
- [ ] Write `original_path` in manifest for imported projects

#### Pre-op snapshots

- [ ] Before destructive operations, create snapshot artifacts in `<project>/.snapshots/`:
  - `manifest-<ISO8601>.json`
  - `<als-name>.<ISO8601>.als`
- [ ] Implement snapshot retention: prune snapshots older than 30 days

### Exit Criteria

- `abletonos new "My Song"` creates correctly structured folder
- `abletonos import --source /path/to/existing` previews and executes import
- Snapshots created before any overwrite/move operation

---

## Phase 4 — Sample Import & Provenance

**Duration:** 3–5 days
**Goal:** `add-samples` wizard copies samples with provenance tracking.

### Tasks

- [ ] Implement `add-samples` wizard:
  - Interactive file/folder picker (macOS native or `tkinter` dialog)
  - Prompt for pack-slug (validated: `^[a-z0-9-]{1,64}$`)
- [ ] Copy samples to `Project/Samples/[pack-slug]/` preserving original filenames
- [ ] Use `shutil.copy2` to preserve mtime
- [ ] Compute SHA-256 checksum for each copied file
- [ ] Populate `manifest.resources` with:
  - `resource_uuid` (UUID v4)
  - `path`: relative path inside project
  - `source_filename`: original filename at import
  - `size_bytes`, `mtime`, `sha256_checksum`
  - `extraction_status`: `"none"` (default)
- [ ] Atomic manifest update (lock → read → validate → update → atomic write → unlock)
- [ ] Sync to PocketBase after manifest write:
  - `bulk_upsert_resources()` for new samples
  - Update project doc `resources_snippet` and `manifest_hash`

### Exit Criteria

- `abletonos add-samples` copies files to correct `Samples/[pack-slug]/` path
- Manifest resources contain correct provenance (checksum, source, size, mtime)
- PB reflects new resources on next `index` run

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
| 3 | Project Creation & Import | 3–5 days | 8–14 days |
| 4 | Sample Import & Provenance | 3–5 days | 11–19 days |
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
