# Ableton Project CLI — Developer Specification (MVP)

Version: 1.0.0
Target audience: implementation engineers working from the agreed one‑pager and clarified decisions.

This document is a developer‑ready specification describing architecture, data models, runtime behavior, CLI contracts, error handling, testing, and an ordered implementation plan so an engineer can begin building the MVP immediately.

Table of contents
- Goals & scope
- High-level architecture
- Runtime & deployment assumptions
- Filesystem layout & conventions
- CLI surface (commands & flows)
- Project manifest (JSON Schema + examples)
- PocketBase (PB) integration: collections & sync contract
- Data flow & state management (locking, atomic writes, snapshots)
- Filesystem operations (sample import, versioning, export)
- Error handling & rollback strategies
- Logging, auditing & diagnostics
- Security & operational notes
- Tests & acceptance criteria
- Implementation sequence & task breakdown
- Developer notes, helpful snippets & references
- Acceptance checklist

---

## Goals & scope

MVP purpose (recap)
- Guided macOS CLI to standardize Ableton project folders, manage sample imports and provenance, enforce .als naming/versioning, provide portable ZIP exports, and a fast cross-project search index via PocketBase.
- Personal single-user CLI (private); no packaging to PyPI required; no hooks/extensions; rsync backup engine removed (user will manage backups manually).

In-scope (MVP)
- init-config (XDG style defaults)
- new/create project wizard (preview plan → create)
- import standardization of existing projects
- add-samples (pack-slug validated; copy; provenance recorded)
- version command for .als (copy-and-increment)
- export-archive (ZIP containing assets + manifest + README)
- PocketBase integration (persistent PB by default; projects/resources/audit collections)
- Atomic manifest writes with file locking; pre-op snapshots for destructive ops (manifest + affected .als)
- SHA-256 checksums for resources
- Unit tests (minimal set)
- Logging/audit: structured audit records in PB + local PB log file

Out-of-scope (MVP)
- rsync backup engine & launchd integration
- Extensions/hooks
- Binary verification for PB download (explicitly opted out)
- Deduplication, audio metadata extraction, attachments in PB, finder tags automation

---

## High-level architecture

Components
- CLI application (Python >= 3.11, Typer) — single binary/script executed by the user.
- Local state on disk under XDG-style dotpaths (user-configurable):
  - Config: ~/.abletonOS/config
  - DB/data: ~/.abletonOS/db
  - Logs: ~/.abletonOS/logs
  - Templates: ~/.abletonOS/templates
- PocketBase (macOS arm64 binary) — persistent process by default; local DB, admin user created at init-config.
- Project folders under user-defined project root (default unset; user configures it).

Data responsibilities
- CLI: manages file operations, manifest.json, snapshot files, zip export, and PB metadata sync.
- PB: stores searchable project & resource metadata (documents) and a dedicated audit collection.
- Filesystem: stores assets (samples, .als files); manifests are canonical on-disk.

Process boundaries
- CLI writes manifest atomically to disk; then syncs a project summary and resource entries to PB.
- PB is authoritative for search / index; manifest.json remains canonical per-project.

---

## Runtime & deployment assumptions

- Platform: macOS (latest). Implementation will not target other OSes in MVP.
- Python target: >= 3.11 (tested on latest stable 3.11.x).
- Distribution: repo/checkout install (pip install -e . or local wheel). No PyPI publish required.
- PocketBase binary:
  - Download latest macOS arm64 release at first run.
  - Store binary and record exact version in config for reproducibility.
  - No checksum verification (MVP decision).
  - Default PB lifecycle is persistent: `pb start` / `pb stop` helpers; CLI can also run ephemeral PB on demand (flag).
- Filesystem defaults: XDG-style under ~/.abletonOS (config, db, logs, templates). User must set a project root during init-config.

---

## Filesystem layout & naming conventions

Default project root: user-configured at init-config. Example project layout (defaults):
- <PROJECT_ROOT>/2026/04/2026-04-12 My Song Project/
  - README.md
  - manifest.json
  - Samples/
    - my-pack-slug/
      - kick-01.wav
  - My Song Project_v1.als
  - .snapshots/
    - manifest-20260412T110523.json
    - My Song Project_v1.als.20260412T110523

Project folder conventions
- Folder name begins with ISO date: YYYY-MM-DD <human name>
- Project-level manifest.json is canonical machine metadata
- Samples copied to: Project/Samples/[pack-slug]/[original_filename]
- .als versioning: file name ends with _vN. Version operation copies the .als to a new file with incremented vN and updates version_history in manifest.

XDG-style CLI data paths (defaults)
- Config dir: ~/.abletonOS/config/
- DB/data dir: ~/.abletonOS/db/
  - PB binary: ~/.abletonOS/db/pocketbase/<version>/pocketbase
  - PB DB data: ~/.abletonOS/db/pocketbase/data/
- Logs dir: ~/.abletonOS/logs/
  - pb log: ~/.abletonOS/logs/pocketbase.log
  - cli logs: ~/.abletonOS/logs/cli.log
- Templates: ~/.abletonOS/templates/

Snapshot storage (per-project)
- Project/.snapshots/ (hidden inside project)
  - manifest-YYYYMMDDTHHMMSS.json
  - <als-filename>.<timestamp> (binary copy)
- Retention: snapshots older than 30 days are pruned on CLI invocation that would create or examine snapshots.

---

## CLI surface (commands & interactive flows)

All commands are interactive/wizard-first by default. No destructive action occurs without an explicit y/n confirmation in the preview step.

Tool entrypoint: `abletonproj` (or chosen package entry). Uses Typer.

Top-level command groups & signatures (representative):

- init-config
  - Purpose: create initial config with default paths & PB settings; prompts for project root and PB admin password (not persisted).
  - Flags: --project-root PATH, --pb-ephemeral (start ephemeral PB instead), --yes (only for automation; discouraged)
- new / create
  - Purpose: interactive wizard to create a new project folder (date-first naming), README.md, manifest.json template.
  - Flags: --name "My Song", --date YYYY-MM-DD, --preview-only
- import
  - Purpose: standardize existing project folder into the convention; shows preview, resolves conflicts.
  - Flags: --source PATH, --preview-only
- add-samples
  - Purpose: interactive select files/folders from sample library; prompt pack-slug; copy into Samples/[pack-slug]/ and update manifest.
  - Flags: --extract (disabled by default; future)
- version
  - Purpose: copy-and-increment .als file (ProjectName_vN.als → _vN+1.als), update version_history in manifest.
  - Flags: --als-file PATH, --message "notes"
- export-archive
  - Purpose: create a portable ZIP of project assets, manifest.json, README.
  - Flags: --dest PATH
- pb
  - Subcommands: start, stop, status
  - start: ensures PB binary exists, launches PB persistent process; if PB not initialized, initializes DB and triggers admin creation via CLI prompt.
  - stop: stop PB process
  - status: show PB status & connection info
- search
  - Purpose: interactive PB-backed search (faceted)
  - Flags: --query, (wizard offers filters)
- index / reindex
  - Purpose: perform PB index sync for a project or all projects (scan manifests and create/update PB documents)
- apply-finder-tags — omitted in MVP (out-of-scope)
- logs
  - Purpose: show tail of CLI log or PB log (--pb flag)

Preview step
- Any action that changes filesystem or deletes items must show a concise preview plan with actions grouped (create dirs, copy files, write manifest, create snapshot, start PB change). User must Approve / Edit / Abort.

Confirmation for destructive ops
- Always explicit y/n in interactive wizard. No `--force` default.

CLI flags for automation
- Provide minimal machine-friendly flags (e.g., --yes) but avoid encouraging automation without user awareness.

---

## Project manifest: canonical JSON Schema

Manifest is canonical single file per project: manifest.json. Must be written atomically (temp-file + rename) and validated against published schema.json.

Manifest top-level schema (JSON Schema for reference)

JSON Schema (abridged; include in codebase as `schema.json`):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Ableton Project Manifest",
  "type": "object",
  "required": [
    "schema_version",
    "project_uuid",
    "project_name",
    "created_at",
    "updated_at",
    "generated_by",
    "resources",
    "version_history",
    "cli_version"
  ],
  "properties": {
    "schema_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "project_uuid": { "type": "string", "format": "uuid" },
    "project_name": { "type": "string" },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "generated_by": { "type": "string" },
    "original_path": { "type": "string" },
    "project_root": { "type": "string" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "finder_tags": { "type": "array", "items": { "type": "string" } },
    "resources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "resource_uuid",
          "path",
          "source_filename",
          "size_bytes",
          "mtime",
          "sha256_checksum"
        ],
        "properties": {
          "resource_uuid": { "type": "string", "format": "uuid" },
          "path": { "type": "string" },
          "source_filename": { "type": "string" },
          "sidecar_present": { "type": "boolean", "default": false },
          "size_bytes": { "type": "integer", "minimum": 0 },
          "mtime": { "type": "string", "format": "date-time" },
          "sha256_checksum": { "type": "string", "minLength": 64, "maxLength": 64 },
          "tags": { "type": "array", "items": { "type": "string" } },
          "finder_tags": { "type": "array", "items": { "type": "string" } },
          "extraction_status": { "type": "string", "enum": ["none", "queued", "extracted"] },
          "audio_metadata_summary": { "type": ["object", "null"] }
        }
      }
    },
    "backups": {
      "type": "array",
      "items": { "type": "object" }
    },
    "version_history": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "als_filename": { "type": "string" },
          "version_number": { "type": "integer" },
          "created_at": { "type": "string", "format": "date-time" },
          "note": { "type": "string" }
        }
      }
    },
    "cli_version": { "type": "string" }
  },
  "additionalProperties": false
}
```

Notes:
- schema_version: semantic versioning, e.g., "1.0.0"
- resource_uuid: unique id per resource (UUID v4). Useful for PB mapping.
- sha256_checksum: lowercase hex string of SHA-256 (64 hex chars).

Example minimal manifest snippet:

```json
{
  "schema_version": "1.0.0",
  "project_uuid": "3f2b9e04-...-abcd",
  "project_name": "2026-04-12 My Song Project",
  "created_at": "2026-04-12T11:05:23Z",
  "updated_at": "2026-04-12T11:05:23Z",
  "generated_by": "abletonproj-cli v0.1.0",
  "original_path": "/Users/me/OldProjects/MySong/",
  "tags": ["pop", "vocal"],
  "resources": [
    {
      "resource_uuid": "a1b2c3d4-...",
      "path": "Samples/my-pack-slug/kick-01.wav",
      "source_filename": "kick-01.wav",
      "sidecar_present": false,
      "size_bytes": 123456,
      "mtime": "2026-04-11T09:12:00Z",
      "sha256_checksum": "0123abcd...",
      "tags": ["kick", "dry"],
      "extraction_status": "none"
    }
  ],
  "version_history": [
    {
      "als_filename": "My Song Project_v1.als",
      "version_number": 1,
      "created_at": "2026-04-12T11:05:23Z",
      "note": "Initial create"
    }
  ],
  "cli_version": "0.1.0"
}
```

Manifest handling rules
- Validate manifest against schema on write and read where appropriate.
- Writes must be atomic (write to temp file adjacent to manifest, fsync, rename).
- Include a `manifest_version` integer (optional helpful internal field) or rely on updated_at for optimistic concurrency. We suggest adding `manifest_version` to manifest to ease conflict detection. (If added, increment on every write.)

---

## PocketBase integration: collections and API contract

PB purpose: searchable, global index of project metadata and resources + structured audit. PB does not store binary attachments.

PB default runtime
- Persistent by default (user runs `pb start` helper); CLI ensures PB binary exists and launches it.
- PB web UI is available locally for inspection (e.g., http://127.0.0.1:8090).
- CLI will create admin user at init-config (prompts for password) using PB Admin API.

Configuration
- PB binary path: ~/.abletonOS/db/pocketbase/<version>/pocketbase
- PB data dir: ~/.abletonOS/db/pocketbase/data
- PB logs: ~/.abletonOS/logs/pocketbase.log
- PB version recorded in CLI config (so subsequent runs can use the same PB binary unless overridden).

Collections (MVP)
1. projects
   - Fields:
     - id (automatic PB id)
     - project_uuid (string, indexed, unique)
     - project_name (string)
     - created_at (datetime)
     - updated_at (datetime)
     - project_path (string) — absolute or configured relative
     - tags (array/string)
     - finder_tags (array/string)
     - version (integer or string)
     - cli_version (string)
     - resources_snippet (string) — small text snippet or aggregated searchable text from resources for FTS
     - manifest_hash (sha256) — optional checksum of the manifest for quick change detection
   - Indexes: project_uuid unique, FTS on project_name, tags, resources_snippet.

2. resources
   - Fields:
     - id (automatic)
     - resource_uuid (string, unique)
     - project_uuid (string) — relation to projects.project_uuid
     - path (string) — relative path within project
     - filename (string)
     - sha256_checksum (string)
     - size_bytes (int)
     - mtime (datetime)
     - pack_slug (string)
     - tags (array)
   - Indexes: FTS on filename, pack_slug, tags, sha256, project_uuid.

3. audit
   - Fields:
     - id (automatic)
     - timestamp (datetime)
     - event_type (string) — e.g., project.create, project.update, samples.add, version.bump, export.archive
     - project_uuid (string; optional)
     - user_message (string optional)
     - payload (object, JSON) — structured event data for later inspection
   - Use this collection to answer "what happened and when" queries.

PB sync contract (high level)
- On project create/update:
  1. CLI writes manifest atomically to disk.
  2. CLI upserts the projects document in PB with a summary of manifest fields and a resources_snippet aggregated.
  3. CLI upserts resources documents per manifest.resources (create or update resource docs).
  4. CLI writes an audit entry recording the operation and success/failure.

- On add-samples:
  - After manifest write, upsert affected resources to PB.
  - Record an audit event.

- On version bump:
  - Update manifest, add version_history entry, upsert project doc (update version), record audit.

- On reindex:
  - CLI can re-scan disk manifests and perform upserts for projects/resources.

HTTP usage
- Use PB HTTP REST API (no driver dependency required). Use a small wrapper module that:
  - Ensures PB is running and reachable.
  - Handles auth for admin operations (use admin token created on init-config).
  - Exposes convenient `upsert_project(manifest)`, `upsert_resource(resource_obj)`, `bulk_upsert_resources(project_uuid, resources_list)`, `write_audit(event)`.

Important PB behavior
- PB attachments are not used for assets — assets remain on disk.
- PB is used for metadata and FTS-backed search.
- PB admin account is created via CLI during init-config (the CLI calls PB API to create a user with admin privileges).

PB lifecycle helpers
- pb start: spawn process; write PID file into ~/.abletonOS/db/pocketbase/pid or similar; stream logs to pocketbase.log.
- pb stop: read PID & kill or use PB stop endpoint (if available).
- pb status: health-check via HTTP or check PID.

---

## Data flow & state management

High level for a sample operation (add-samples):
1. Acquire a per-project manifest file lock (portalocker) with timeout and retries.
2. Read manifest.json -> validate schema.
3. Generate the planned operations list (copy file A → Samples/pack-slug/A).
4. Show preview to user.
5. If destructive op, create pre-op snapshot (manifest copy + copy of .als if relevant).
6. Copy files to destination (use shutil.copy2 to preserve mtime; validate write success).
7. Compute SHA-256 checksum for new files and collect metadata (size, mtime).
8. Update manifest.resources: append new resource objects with UUIDs and metadata.
9. Atomic write manifest.json (temp + fsync + rename).
10. Release file lock.
11. Sync changes to PB: upsert project, bulk_upsert_resources, write audit.

Locking & concurrency
- Use a per-project lock file: <project>/manifest.json.lock or a dedicated lock manager keyed by project_uuid.
- Use `portalocker` (or fcntl wrapper) for robust advisory locking across processes.
- Lock acquisition:
  - Default timeout: 30s (configurable).
  - Exponential backoff on retries; if lock not acquired, inform user and provide option to abort or force-wait longer.

Optimistic conflict detection
- Each manifest write increments `manifest_version` and sets `updated_at`.
- If PB sync detects that PB's stored manifest_hash differs from local manifest hash or manifest_version mismatch on upsert, treat as conflict: reload manifest, present diff to user and prompt for retry or abort.

Atomic manifest write pseudocode (Python):

```python
def atomic_write_manifest(manifest_path: Path, manifest_obj: dict):
    temp = manifest_path.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(manifest_obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(manifest_path)  # atomic rename on POSIX
```

Snapshot creation
- Before destructive operations (delete, overwrite .als, rename), create snapshot artifacts into Project/.snapshots/.
  - snapshot manifest: manifest-<ISO8601>.json
  - snapshot of .als: <als-name>.<ISO8601>.als (binary copy)
  - preview_plan.json: optional representation of planned operations
- Pruning: on CLI invocation or snapshot creation run a prune function to delete .snapshots/* older than 30 days.

---

## Filesystem operations & behaviors

Sample copy rules
- add-samples:
  - Prompt for pack-slug: must match regex ^[a-z0-9-]{1,64}$ (kebab-case).
  - Copy preserving original filename into Project/Samples/[pack-slug]/.
  - No dedupe (file identity not deduped in MVP).
  - Compute SHA-256 on destination file.
  - Populate resource object with path relative to project root.

als versioning
- `version` command:
  - Identify the latest _vN.als file for the project (parse filenames).
  - Create a copy: _vN+1.als
  - Optionally copy attached Ableton Backup folder not necessary for MVP.
  - Update manifest.version_history with entry containing filename, version_number, created_at, note.
  - Snapshot previous .als file into .snapshots/ with timestamp before copy (as "last saved .als" snapshot behavior).

Export archive
- `export-archive`:
  - Create a ZIP file with the following contents rooted at top-level dir <project_name>:
    - README.md
    - manifest.json
    - Samples/ (all sample files included)
    - All *.als files
    - version_history and other metadata included in manifest.json
  - Ensure relative paths preserved; ensure zip writes are atomic (create temp zip and rename).
  - Optionally provide an `--export-db` flag (out-of-scope for MVP unless requested later).

Import flow
- `import`:
  - Accept a source folder path.
  - Analyze structure: locate .als files, Samples folders.
  - Plan a target project folder under configured project root using date-first convention.
  - Preview move/copy operations: default behavior should be copy (not move) to avoid destructive changes; allow user to opt-in to move with explicit confirmation.
  - Handle name collisions by incrementing a suffix or prompting user.

Indexing & reindexing
- `index` / `reindex`:
  - Scan configured project root recursively for manifest.json files.
  - For each manifest found, call PB upsert flows.
  - For new projects lacking manifest, prompt to import or create skeleton manifests.

---

## Error handling strategies

General principles
- Fail fast with clear human-friendly error messages.
- On any filesystem operation failure, provide:
  - error summary for the user
  - a suggested command or step to recover
  - retention of pre-op snapshot (if created) so user can recover
- Keep manifest integrity: do not leave partially written manifest.json. Always use atomic write + lock.

Categories & behaviors

1. Filesystem errors (permissions, disk full, path not found)
   - Detect low disk space before large copy operations when possible (use shutil.disk_usage).
   - On copy/write failure: stop operation, present error, keep snapshots for restore, log error to local logs and PB audit.
   - Provide a helpful hint (e.g., "free X MB and retry").

2. Lock acquisition timeout
   - If lock not acquired within timeout: notify user which PID holds lock (if available) and options: retry longer, abort.
   - Avoid forceful unlocking unless user explicitly requests.

3. Manifest validation failure
   - If reading manifest fails schema validation:
     - Do not overwrite manifest.
     - Offer to back up broken manifest (copy to .snapshots/) and attempt to repair (prompt user).
     - Allow `--force` reinitialization only with explicit confirmation.

4. PB unavailability / network error
   - PB is local: but if PB not running or unresponsive:
     - For operations that require PB (search, index), show helpful message and offer to `pb start`.
     - For operations that write to disk (add-samples, version), allow them to succeed offline and enqueue PB sync attempts when PB is available (write a `pending_sync.json` record in ~/.abletonOS/db/queue/).
     - Provide CLI command `sync-pending` to flush queued syncs.

5. PB admin creation failure
   - If the CLI cannot create the admin user automatically:
     - Keep PB running.
     - Open admin UI and instruct user to create admin manually with instructions.
     - Record partial state in config so next attempt can retry.

6. Checksum mismatch post-copy
   - If checksum of copied file does not match expected (rare):
     - Delete the destination file (if corrupted), retry copy up to N times (default 3).
     - If retry fails, mark resource as "checksum_mismatch" in manifest/resources and record audit.

7. PB sync errors & conflicts
   - If PB upsert fails due to a conflicting concurrent change:
     - Reload manifest and PB record; present a merge/diff prompt to user.
     - Allow retry or abort; also support a CLI flag to force overwrite PB metadata.

Rollback strategy
- For multi-step operations:
  - Use an operation log in memory and snapshot before starting destructive steps.
  - If operation fails mid-way:
    - Attempt best-effort rollback (remove copied files if operation was additive, restore .als from snapshot if needed).
    - If rollback not possible, keep snapshot + pending operation details in ~/.abletonOS/db/operations/ to assist manual recovery.
  - Always write an audit event recording failure, error message, and location of snapshot.

User-facing errors
- Provide human-friendly messages in the interactive wizard including:
  - short error text
  - reason (technical)
  - suggested next steps (commands to run)
  - path to logs and snapshot location

---

## Logging, auditing & diagnostics

Logging
- Use Python logging module.
- Log levels:
  - INFO by default.
  - DEBUG when `--debug` or environment variable `ABLETON_PROJ_DEBUG=1` is set.
- Local log files (rotating):
  - CLI log: ~/.abletonOS/logs/cli.log (rotating, keep last 7 files)
  - PB log: ~/.abletonOS/logs/pocketbase.log (PB process writes here)
- Console output:
  - Keep concise human messages; verbose logging should be in files.

Audit
- Structured audit events stored in PB `audit` collection for important operations:
  - event_type, timestamp, project_uuid, payload (structured)
  - Useful queries: recent operations, who did what (single-user), last sync statuses.
- Also record minimal local audit log in ~/.abletonOS/db/audit-local.jsonl for redundancy (newline-delimited JSON).

Diagnostics
- `abletonproj diagnose` command:
  - Check PB status, disk free, config validity, list pending sync tasks, and recent CLI logs.
  - Produce a concise report and a tarball of relevant logs & small manifest snapshots for debugging.

---

## Security & operational notes

- PB binary download has no checksum verification (MVP decision). This is a security trade-off for simplicity; a later enhancement should add SHA-256 pinning and signature verification.
- Admin password:
  - CLI prompts for admin password during init-config and uses it to create the PB admin user. CLI does NOT persist the password.
- PB binds to localhost by default. No remote exposure in MVP.
- No hooks/extensions in MVP; do not execute arbitrary code in the project directory.
- Manifest and snapshot files should have typical user file perms; do not change default OS ACLs.

---

## Tests & acceptance criteria

Unit tests (local only)
- test_manifest_atomic_write: verify temp write + rename ensures full manifest content on success; simulate failure to confirm no partial writes.
- test_checksum_sha256: compute and verify sha256 for sample files (corner cases: zero-length file).
- test_file_locking: simulate concurrent writes with threads/processes and confirm lock serialization.
- test_version_command: ensure _vN→_vN+1 naming, snapshot created, manifest updated.
- test_export_archive: verify zip contains expected files and manifest matches manifest.json inside ZIP.
- test_pb_start_stop_helpers: mock subprocess and check CLI logic for starting/stopping PB records state appropriately.

Integration tests (optional / manual)
- manual flow: init-config → pb start → create new project → add-samples → version → export-archive → search via PB UI.
- Reindex flow: create several projects, run `index` and confirm PB has project/resource docs.

Acceptance checklist (MVP)
- init-config wizard saves config to ~/.abletonOS/config
- new/create wizard creates folder with README.md and valid manifest.json
- import wizard standardizes existing project
- add-samples copies files to Samples/[pack-slug]/ and writes provenance to manifest
- version command increments .als version and updates version_history and snapshot
- export-archive creates usable ZIP with asset files and manifest
- pb helper commands: start/stop/status work and admin created via CLI
- index & search using PB (PC local UI accessible)
- Atomic manifest writes + file locking + snapshot/retention implemented
- Unit tests added to repo

---

## Implementation sequence & task breakdown

Prioritized ordered tasks with suggested scope/owners:

Phase 0 — repo + scaffolding (1-2 days)
- Initialize repo, pyproject.toml, minimal packaging.
- Create Typer CLI skeleton.
- Set up config module and path constants (XDG defaults: ~/.abletonOS/…).
- Add logging config & simple CLI-level logging writer.

Phase 1 — Config & PB bootstrap (2-4 days)
- Implement `init-config` wizard:
  - Prompt for project root, PB admin password (prompt; do not persist).
  - Create default directories: ~/.abletonOS/config, ~/.abletonOS/db, ~/.abletonOS/logs
  - Download PB binary latest arm64 release and store in ~/.abletonOS/db/pocketbase/<version>/pocketbase; record version in config.
  - Provide `pb start` helper that launches PB persistent process and writes PB pid file and logs.
  - Implement admin creation via PB API (post-start).
- Unit tests: pb helpers mocked.

Phase 2 — Manifest API & atomic write + locking (2-3 days)
- Implement manifest model classes (pydantic or dataclasses) and load/validate against schema.json.
- Implement atomic write helper and portalocker-based lock manager.
- Unit tests: manifest atomic write & locking.

Phase 3 — new/create & import flows (3-5 days)
- Implement `new` wizard with preview, create folder structure, README.md, baseline manifest.
- Implement `import` flow: scanning, preview, copy/collapse into new folder.
- Ensure snapshots for overwrite/destructive cases.

Phase 4 — add-samples & resource handling (3-5 days)
- Implement pack-slug validation, copy logic (copy2 + checksum), update manifest.resources atomically.
- Implement SHA-256 checksum module.
- After manifest write, call PB upsert resource + project summary.
- Unit tests: add-samples core functions.

Phase 5 — version command & snapshots (2-3 days)
- Implement detection of latest vN .als and copy to vN+1.
- Snapshot previous .als into .snapshots/ before copying.
- Update manifest.version_history.
- PB sync update.

Phase 6 — export-archive & reindex/search (2-4 days)
- Implement export-archive logic (atomic zip creation).
- Implement `index` / `reindex` that scans manifests and upserts to PB.
- Implement `search` interactive wizard (initial simple filters).

Phase 7 — audit & diagnostics (2 days)
- Implement writing audit events to PB when operations succeed/fail.
- Implement `diagnose` command to collect logs, check PB health, and list pending syncs.

Phase 8 — polishing & tests (2-4 days)
- Add unit tests for core modules.
- Manual acceptance testing flows & documentation for first-run.
- Add README, usage docs, and example config.

Total rough MVP engineering effort estimate: ~3–5 weeks of focused development for a single engineer (depends on experience and available PB familiarity). These estimates assume a small, focused scope with limited extensibility.

---

## Developer notes & helpful code snippets

Recommended Python packages (dependencies)
- typer >= 0.6
- rich (for nicer interactive UIs) — optional but recommended
- portalocker >= 2.7
- requests >= 2.28 (for PB downloads & REST)
- pydantic >= 1.10 or dataclasses + jsonschema for manifest validation
- pytest (for tests)
- packaging.version (to handle PB version strings)
- hashlib (stdlib) for sha256
- zipfile (stdlib) for export-archive
- shutil, os, pathlib (stdlib)
- subprocess for PB process management

Sample atomic write function (complete version):

```python
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

def atomic_write_json(path: Path, obj: dict, mode=0o644):
    dirpath = path.parent
    with NamedTemporaryFile('w', dir=dirpath, delete=False, encoding='utf-8') as tmp:
        json.dump(obj, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.chmod(tmp.name, mode)
    os.replace(tmp.name, path)  # atomic on POSIX
```

Sample SHA-256 streaming:

```python
import hashlib

def sha256_file(path: str, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()
```

PB upsert pseudocode:

```python
def upsert_project(pb_base_url, admin_token, manifest):
    doc = {
        "project_uuid": manifest["project_uuid"],
        "project_name": manifest["project_name"],
        "created_at": manifest["created_at"],
        "updated_at": manifest["updated_at"],
        "project_path": manifest.get("project_root") or compute_project_path(manifest),
        "tags": manifest.get("tags", []),
        "cli_version": manifest["cli_version"],
        "resources_snippet": " ".join(r["source_filename"] for r in manifest["resources"][:20]),
        "manifest_hash": sha256_of_json(manifest),
    }
    # PB upsert: try to find by project_uuid else create
    # Use PB collections REST endpoints to create or update record
```

PB admin creation flow:
- After PB process started and healthy:
  - Use REST Admin API to create admin user. If the API is not available programmatically for initial user creation, open PB admin UI and instruct user to create the account. For MVP we prefer automated creation via API if PB supports it.

---

## Edge cases & boundary conditions

- Very large sample imports (multi-GB):
  - Warn user if total copy size exceeds available disk.
  - Consider chunked copies and progress reporting.
- Interrupted operation (kill mid-copy):
  - Leftover partial files should be detected and cleaned up on next run (compare manifest entries vs on-disk).
  - Keep snapshot to allow recovery.
- Very large manifests / many resources:
  - PB upsert bulk operations: use batching (e.g., 100 resources per batch) to avoid high memory/HTTP overhead.
- Concurrent PB writes from multiple CLI instances:
  - PB is persistent but single-user; still add optimistic retry/backoff on upsert errors.
- Corrupt manifest.json:
  - Back up then attempt a best-effort repair or present user with options.

---

## Acceptance checklist (developer-run tests & manual QA)

Automated unit tests pass:
- manifest atomic write & validation
- sha256 checksum tests
- file lock concurrency tests

Manual flows to confirm:
- init-config: config files created under ~/.abletonOS/config and PB is downloaded and started; admin created via CLI.
- new: create new project -> folder created with README and valid manifest.
- add-samples: add file(s) -> files in correct Samples/[pack-slug] path and manifest updated with SHA-256.
- version: bump .als file -> new .als created, snapshot created for previous .als, manifest version_history updated.
- export-archive: ZIP contains manifest and assets and is valid.
- PB search: projects & resources show up in PB; audit records created for operations.
- Snapshot retention: create snapshots older than 30 days (manually change mtime), run prune, confirm deletion.

---

## Final notes & recommended next steps

- Implement core filesystem + manifest behavior first; PB integration can be added in parallel but try to keep PB sync as a separate layer with robust offline queueing to avoid blocking good offline behavior.
- Keep the CLI interactive UX consistent and safe: always present a preview and confirm destructive operations.
- Add TODOs in the codebase to mark future security improvements (PB binary checksum verification, optional attachment sync, automated backups).
- Document install and first-run experience (how to run init-config, pb start, and create projects).
- Keep the manifest schema immutable for minor changes where possible; when changing the schema in future versions, provide migration tooling.

---

If you want, I can produce:
- A ready-to-run project skeleton with module layout and stubbed functions.
- The concrete JSON Schema file (full, linted).
- A set of Pytest unit tests skeleton.
- A sample `init-config` wizard script.

Tell me which of the above you want next (skeleton repo, schema file, tests, or start implementing a specific command).