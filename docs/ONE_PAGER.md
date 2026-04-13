# Ableton Project CLI — One‑Pager (MVP)

Purpose
- Provide a safe, guided macOS CLI that standardizes Ableton project folders, manages sample imports with provenance, enforces naming/versioning conventions, provides rsync-style backups and portable exports, and enables fast cross-project search — all through an interactive wizard-style UX (not script-first).

Problem (pain)
- Producers accumulate inconsistent Ableton project folders and scattered samples, making collaboration, backups, and discovery hard.
- Manual sample imports risk losing provenance; ad-hoc naming/versioning creates duplicate projects and confusion.
- Searching across many projects is slow without a single index.

Target audience / ideal customer
- Single-musician Ableton users on macOS who prefer guided, safe tooling over scripting; have local sample libraries and want repeatable organization, safe backups, and quick find/restore workflows.

MVP goals (what this MVP must do)
- Create new Ableton project folders using a date-first convention and produce a README + manifest (no .als creation).
- Import/standardize existing projects into the structure.
- Enforce naming templates and version suffixing for .als files (copy-and-increment approach).
- Copy selected samples into Project/Samples/[pack-slug]/ and record provenance in a single project manifest.json.
- Provide a global index (PocketBase) for fast cross-project search and tags.
- Provide backup/export: one-off rsync-style backup and portable ZIP exports.
- Provide interactive guided search & tagging flows.
- Support lightweight extensions/hooks (pre/post-create) with checksum white-listing and per-hook modes.

Platform & tech choices (final)
- Platform: macOS only (MVP).
- Implementation: Python 3.10+ (Typer CLI), pathlib/os for FS, PyYAML for config parsing, optional xxhash for hashing if needed.
- Index / global metadata backend: PocketBase (local), auto-downloaded & managed by the CLI.
- Backup engine: rsync (preferred) with Python shutil fallback if needed.
- Config & runtime paths (macOS conventions):
  - App data & config: ~/Library/Application Support/<bundle-id>/
  - PocketBase data: ~/Library/Application Support/<bundle-id>/pocketbase/ (configurable)
  - Logs: ~/Library/Logs/<bundle-id>/
  - Templates & extensions: ~/Library/Application Support/<bundle-id>/{templates,extensions}/ (configurable)
- Projects default root (example): /Users/<user>/Music/Ableton/

Core UX model
- Interactive-only guided wizard for all core flows (init-config, new, import, add-samples, version, backup, search, tag).
- Preview step (default) before any filesystem changes: concise, human-friendly plan; options: Approve / Edit / Abort.
- Always require explicit y/n confirmation for destructive actions (no --force flag).
- No audio preview/play feature in the MVP.
- Config created via init-config and stored in macOS App Support path; CLI flags can override config values.

Folder & naming conventions (default)
- Root layout (default Option A with nested Year/Month):
  /Users/<you>/Music/Ableton/2026/04/2026-04-12 My Song Project/
    - README.md (human docs)
    - manifest.json (canonical machine metadata)
    - Samples/
      - my-pack-slug/
        - kick-01.wav
    - [ProjectName]_v1.als
    - Backup/ (Ableton generated)
- Project folder name begins with YYYY-MM-DD (hyphen-separated).
- .als versioning: filenames use _v# suffix (ProjectName_v1.als → ProjectName_v2.als via `version` command).

Project metadata model (manifest.json)
- Single project-level manifest.json is canonical (no per-asset sidecar files for MVP).
- Manifest must be written atomically (temp-file + rename).
- Suggested (required) manifest schema fields:
  - schema_version (string)
  - project_uuid (UUID v4)
  - project_name (string)
  - created_at / updated_at (ISO 8601)
  - generated_by (tool/version)
  - original_path (if imported)
  - tags (string[])
  - finder_tags/colors (string[] / codes)
  - resources: array of resource objects:
    - path (relative path inside project)
    - source_filename (original filename at import)
    - sidecar_present (bool; always false in MVP)
    - size_bytes
    - mtime (ISO 8601)
    - sha256_checksum
    - tags (string[])
    - finder_tags (string[])
    - extraction_status (enum: none | queued | extracted)
    - optional audio_metadata_summary (object; present only if extraction enabled)
  - backups (summary entries)
  - version_history (list of .als version entries)
  - cli_version
- Manifest must include a published JSON Schema for validation (engineers: add schema.json).

Sample handling & provenance (behavior)
- add-samples flow:
  - Interactive prompt: select files/folders from sample library.
  - Prompt user for a pack-slug (validated to kebab-case [a–z0–9-], max length) and store it in manifest and README.
  - Copy samples into Project/Samples/[pack-slug]/[original_filename] (no renaming).
  - No deduplication in MVP: identical files from different packs are stored separately.
  - Record provenance (original path, checksum, size, date_added) in manifest.
  - Audio metadata extraction is disabled by default; available via explicit option (e.g., `--extract`).

Indexing & global metadata backend
- Global index: PocketBase (local) is the canonical global index chosen for MVP.
  - PocketBase is auto-downloaded by the CLI on first run; CLI handles platform selection and version pinning.
  - Default PocketBase data path: ~/Library/Application Support/<bundle-id>/pocketbase/ (configurable).
  - CLI will auto-start PocketBase as an ephemeral child process for commands that need it, with flags:
    - --background (run PB in background)
    - --no-start (skip auto-start)
    - override options for port, data dir, binary path
  - Admin web UI enabled by default on localhost:8090. First-run admin account setup required; CLI prints & opens the admin URL.
  - CLI provides pb subcommands: `pb start`, `pb stop`, `pb status`.
- Rationale: PocketBase provides REST API, FTS-backed search, tags, and a web UI; bundling avoids forcing users to install background services.

Export & portability
- export-archive produces a fully portable ZIP containing:
  - All project assets (Samples/, .als files)
  - manifest.json
  - README.md
- Exports are usable on other machines without PocketBase. Optionally produce PocketBase export artifacts via `--export-db` to rehydrate metadata in a PocketBase instance.

Backups & scheduling
- Backup engine: rsync-style incremental backups (rsync + hardlink strategy), with a Python fallback.
- Default behavior:
  - CLI prints a launchd plist and a one-line install command for users (no auto-install).
  - Default schedule: daily incremental backup (user-configurable).
  - Default retention: last 14 snapshots (configurable).
  - Backup destination: configured default path in config; per-run override allowed via interactive prompt or `--dest`.
- PocketBase snapshot policy:
  - Backups include PocketBase DB/attachments only when PB is placed into maintenance/read-only mode.
  - CLI triggers PB maintenance mode before snapshot and resumes it after snapshot — ensures consistent DB backups.
- Exportable command: `install-backup-instructions` prints launchd snippet and step-by-step instructions (no automatic system changes).

Search & discovery
- Interactive `search` command (wizard):
  - Faceted search (name, tags, BPM/key metadata if present, project date range).
  - Uses PocketBase-backed FTS and metadata fields.
  - Paginated interactive results with actions: Reveal in Finder, Add sample to open project, Show metadata, Export.
  - `index`, `reindex`, and `index-status` commands to manage the global index.

Extensions / hooks
- Location: ~/Library/Application Support/<bundle-id>/extensions/
- Hooks:
  - Support executable hooks and a hooks.json manifest per extension.
  - Hooks disabled by default; user must enable extension execution in config.
  - Each hook must appear on a user-managed whitelist or pass a checksum match before execution.
  - Hooks can be `sync` (default) or `async`; CLI will allow per-hook mode.
  - Hooks run synchronously by default and show stdout/stderr in the wizard, unless configured async.

PocketBase deployment & runtime details
- PocketBase binary is auto-downloaded & cached on first run (CLI handles download & validation).
- CLI-managed runtime:
  - Default: auto-start ephemeral PB process for commands that require it, stream logs to CLI, health-check, and terminate after command finishes.
  - Optional flags: `--background` to run PB persistently; `pb start` / `pb stop` helper commands; ability to install an optional launchd plist if user opts in.
- Web UI & admin:
  - UI enabled by default on 127.0.0.1:8090; CLI prints URL and opens browser.
  - Admin account creation required on first run.

Security & account model
- Single-user local tool: no app-level multi-user features in MVP.
- PocketBase has an admin user — CLI requires secure setup on first run (password creation). PB binds to localhost by default.
- Hooks only run with explicit user opt-in and whitelist.

Logging, auditing & safety
- Logs: written to ~/Library/Logs/<bundle-id>/ on demand (e.g., `--log`, `--debug`) or on errors.
- Audit trail: PocketBase stores recent operation metadata for “recent” / audit; CLI keeps per-run logs when requested.
- Destructive operations: always prompt and create a pre-op snapshot (metadata + minimal file copies) to allow reverting the last operation where practical. No full multi-step undo in MVP.

Constraints, tradeoffs & risks
- Single global PocketBase index is a single point of failure — must be backed up consistently and handled in restores.
- PocketBase adds process lifecycle complexity (managed by CLI), concurrency & crash recovery semantics must be clear.
- No per-asset sidecars by design — single manifest.json must be written atomically; corruption risk if not implemented correctly.
- No Windows support in MVP — keeps scope focused and simplifies symlink/rsync/launchd semantics.
- No audio preview in MVP — reduces dependencies.
- No dedupe — may duplicate identical files on disk; future optional dedupe can be added.

MVP acceptance criteria (developer checklist)
- [ ] Interactive `init-config` wizard creating config file in ~/Library/Application Support/<bundle-id>/config.yaml
- [ ] `new/create` wizard: preview plan → create Year/Month/ YYYY-MM-DD Project folder, README.md, manifest.json template
- [ ] `import` wizard: move/standardize existing projects into structure with conflict handling
- [ ] `add-samples` wizard: prompt pack-slug, copy files into Samples/[pack-slug]/, update manifest.json atomically
- [ ] `version` command: copy-and-increment .als file, update version_history in manifest
- [ ] `backup` / `export-archive` implementations: rsync snapshot & portable ZIP export (ZIP contains manifest + assets)
- [ ] `install-backup-instructions` prints launchd plist + install steps
- [ ] Global PocketBase integration:
    - auto-download PB binary on first run
    - on-demand PB start/stop as child process + pb helper commands
    - admin web UI accessible at localhost:8090; first-run admin setup
    - store project metadata & support search via PB
- [ ] `search` interactive wizard using PB FTS
- [ ] `apply-finder-tags` manual command (opt-in)
- [ ] Extensions: run whitelisted hooks with checksum validation
- [ ] Atomic manifest writes + JSON Schema validation
- [ ] Backup snapshot of PocketBase uses maintenance/read-only mode
- [ ] Logging & error handling with logs in ~/Library/Logs/<bundle-id>/

Engineering notes & immediate risks to address
- Implement manifest.json atomic-rewrite (temp file + rename) and validation against JSON Schema.
- PocketBase binary lifecycle: ensure robust download/verification, caching, and version pinning.
- PocketBase backup snapshot must ensure maintenance-mode before copying DB files.
- Concurrency: define behavior for simultaneous CLI invocations while PB is ephemeral; add retries/locks for index updates.
- Testing: simulate large sample imports and search scaling; validate restore workflows from export ZIPs and PB snapshots.

Operational & support notes
- Dependencies to document: rsync (Homebrew), Python 3.10+, network-only accessed local PB on localhost.
- Provide clear first-run instructions, admin account creation steps, and how to back up PB data dir.
- Include a migration path: optional PocketBase import/export and future PocketBase→SQLite adapter documentation if reverting to a file-only index is required.

Next steps (recommended roadmap items for Product & Eng)
- Week 0: Kickoff, finalize JSON Schema, define bundle-id and exact App Support paths, set up repo & CI.
- Week 1: CLI skeleton (Typer), init-config, new/create wizard with manifest write/read.
- Week 2: add-samples copy + pack-slug prompt + manifest updates; implement atomic manifest writes.
- Week 3: PocketBase auto-download + ephemeral start/stop helper; basic PB metadata sync for created projects.
- Week 4: search wizard (PB-backed), version command, export-archive, backup (rsync wrapper) & launchd instructions.
- Week 5: Extensions/hook runner, apply-finder-tags implementation, logging & audit, E2E tests, docs.
- Deliverable: Production-ready MVP with installation docs and JSON Schema.

Contact / ownership
- Product: define bundle-id and UI/UX copy for all wizard prompts
- Engineering: allocate an owner for PocketBase integration and manifest atomic write
- QA: test backups, exports, PB snapshot restore, and manifest corruption scenarios

---

This one‑pager captures the agreed MVP scope, user flows, data model, and critical engineering constraints. If you approve this content, engineering can use it as a launch pad to produce a technical spec (detailed API, wireframes for wizard prompts, code structure, tests). Tell me if you want the technical-spec next (detailed tasks, data models, API contracts, acceptance tests) or any edits to this one-pager.