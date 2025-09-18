# ROM Curator: Game File Ingestion Implementation Plan

## Overview & Goals
- Deliver a deterministic, resumable workflow that transforms loose files into `rom_file` records linked to releases through `release_artifact`, feeding the existing curation and organization surfaces.
- Bake in observability, configuration governance, and resilience from the first milestone so every component emits actionable telemetry, honors cancellation, and recovers gracefully after interruption.
- Maintain a trustworthy library structure while keeping imports idempotent and observable through the logging and configuration systems already in place.

## End-to-End Workflow Summary
1. User launches **Tools → Library → Scan & Ingest Files…** from `rom_curator_main.py`; the PyQt dialog validates configuration, runs a pre-flight scan, and dispatches an ingestion job through `enhanced_importer_gui.ImportWorkerThread`.
2. Discovery walks configured `library_root` entries breadth-first, recording candidates in `file_discovery`, checkpointing progress, and emitting instrumentation events so throughput and ETA remain visible.
3. Each discovered file is classified (extension registry hints plus header checks), hashed in a streaming fashion with hash-cache reuse, and either linked to an existing `rom_file` or inserted as a new row alongside auxiliary metadata.
4. Archives are expanded virtually: contents are enumerated, hashed, and registered as child `rom_file`s without permanently unpacking unless policy requires it; new `archive_member` records preserve container relationships.
5. For new or changed hashes, the job attempts deterministic DAT matching using `dat_entry` (hash first, then normalized metadata) and `GameMatcher` with `platform_links`. Results populate `dat_atomic_link` or enqueue unresolved items for curation while conflict rules and organizer policies keep the library consistent.
6. Completion produces post-run reports, performance summaries, and (optionally) kicks off library organization moves governed by configured rules and tracked in `file_operation_log`; documentation and benchmarking capture lessons for future runs.

## Phase 1 – Foundation (Work Items 1–3)
### Work Item 1: Database Foundations for Ingestion
- Update `Rom Curator Database.sql` to add foundational tables and columns that unblock downstream workflow stages:
  - `file_discovery`, `archive_member`, `rom_file_metadata`, `file_operation_log`, and `ingestion_queue` tables with the columns and constraints defined below.
  - Column additions on `file_instance` (`first_seen`, `last_modified`, `status`), `release_artifact` (`artifact_sequence`), and `rom_file` (`content_role`) with backwards-compatible defaults.
- Ensure foreign keys, unique indexes, and cascading rules mirror the schema defined in the plan; include migration-safe scripts or guidance so existing deployments can apply the schema updates without data loss.
- Validate schema changes with automated smoke tests that exercise inserts/updates for discovery rows, archive membership, metadata payloads, and operation logging.

```sql
CREATE TABLE IF NOT EXISTS file_discovery (
    discovery_id INTEGER PRIMARY KEY,
    log_id INTEGER NOT NULL REFERENCES import_log(log_id),
    root_id INTEGER NOT NULL REFERENCES library_root(root_id),
    absolute_path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    size_bytes INTEGER,
    modified_time TEXT,
    rom_id INTEGER REFERENCES rom_file(rom_id),
    promotion_state TEXT NOT NULL DEFAULT 'pending' CHECK (promotion_state IN ('pending','hashed','failed')),
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen TEXT NOT NULL DEFAULT (datetime('now')),
    depth INTEGER DEFAULT 0,
    message TEXT,
    UNIQUE(root_id, relative_path)
);

CREATE TABLE IF NOT EXISTS archive_member (
    parent_rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    child_rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    path_in_archive TEXT NOT NULL,
    compressed_size INTEGER,
    uncompressed_size INTEGER,
    compression_ratio REAL,
    is_primary INTEGER DEFAULT 0,
    sort_order INTEGER,
    last_modified TEXT,
    PRIMARY KEY (parent_rom_id, child_rom_id)
);

CREATE TABLE IF NOT EXISTS rom_file_metadata (
    rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    metadata_key TEXT NOT NULL,
    metadata_value TEXT NOT NULL,
    PRIMARY KEY (rom_id, metadata_key)
);

CREATE TABLE IF NOT EXISTS file_operation_log (
    operation_id INTEGER PRIMARY KEY,
    instance_id INTEGER REFERENCES file_instance(instance_id),
    rom_id INTEGER REFERENCES rom_file(rom_id),
    operation_type TEXT NOT NULL CHECK (operation_type IN ('move','copy','delete','quarantine','restore','password_required','error')),
    source_path TEXT,
    destination_path TEXT,
    initiated_by TEXT DEFAULT 'ingestion',
    status TEXT NOT NULL CHECK (status IN ('pending','completed','failed')) DEFAULT 'completed',
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ingestion_queue (
    queue_id INTEGER PRIMARY KEY,
    root_id INTEGER NOT NULL,
    absolute_path TEXT NOT NULL,
    depth INTEGER DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('pending','processing','done','error')) DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Work Item 2: Logging, Error Handling & Resilience
- Add dedicated logging channels (`ingestion`, `ingestion.archive`, `ingestion.organizer`) via `LoggingManager` and ensure the ingestion worker, archive handlers, platform inference, and organizer emit structured events from the start.
- Implement granular error handling that rolls back only the active batch while persisting prior progress; failed entries should stay in `file_discovery` with diagnostic messages and retry metadata.
- Enforce a deterministic retry policy: retry transient failures (SQLite `busy`, network share unavailable, temp extraction race) up to three attempts with exponential backoff (2s, 8s, 18s). Flag non-retryable errors (hash mismatch, corruption, invalid configuration, permission denied) immediately and require operator action.
- Persist checkpoint state frequently, honor cancellation flags promptly, and surface recoverable issues (e.g., permission problems) in the session summary; integrate cancellation/resume paths into automated tests.
- Capture resilience metrics (retries, checkpoint restores) so post-run reports can highlight areas needing attention.

### Work Item 3: Metadata Source Integration & Job Wiring
- Register a `file_ingestion` entry in `metadata_source`, seed scripts, and config defaults so the new workflow can be triggered from both CLI and GUI contexts.
- Implement `scripts/seeders/library_ingestion.py` (or equivalent) seeder using the shared importer base classes, honoring configuration validation and emitting progress telemetry.
- Extend `ImportWorkerThread` to launch the new script, stream logs, emit progress updates, surface pre-flight results, and respect cancellation for ingestion jobs.
- Define and document new `config.json` keys (paths, batching, validation toggles) required for ingestion; update `ConfigManager` defaults and validation so settings exist before downstream work begins.
- Provide unit and integration tests covering CLI invocation, GUI wiring, configuration persistence, and cancellation/resume flows.

## Phase 2 – Core Infrastructure (Work Items 4–7)
### Work Item 4: Extension Registry & Platform Extension UI
- Implement the `file_type_category`, `file_extension`, and `platform_extension` tables with CRUD helper methods seeded with sensible defaults covering ROM, archive, disc, auxiliary, patch, and save content.
- Build a PyQt management dialog to view/filter extensions, toggle activation, assign platform mappings, and import/export extension lists; integrate discovery suggestions for unknown extensions.
- Ensure registry updates immediately influence discovery, hashing, and platform inference routines.
- Add automated UI/service-layer tests validating CRUD operations, persistence, and unknown extension handling.

```sql
CREATE TABLE IF NOT EXISTS file_type_category (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS file_extension (
    extension TEXT PRIMARY KEY,
    category_id INTEGER REFERENCES file_type_category(category_id),
    description TEXT,
    is_active INTEGER DEFAULT 1,
    treat_as_archive INTEGER DEFAULT 0,
    treat_as_disc INTEGER DEFAULT 0,
    treat_as_auxiliary INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS platform_extension (
    platform_id INTEGER REFERENCES platform(platform_id),
    extension TEXT REFERENCES file_extension(extension),
    is_primary INTEGER DEFAULT 0,
    PRIMARY KEY (platform_id, extension)
);
```

### Work Item 5: Platform Detection & Assignment
- Implement platform inference heuristics using extension registry hints, directory naming patterns, and optional user-defined mapping rules declared in `config.json`.
- Provide a manual platform assignment dialog when inference confidence is low; persist operator choices for reuse and validate selections against `platform_links`/`platform_extension` to prevent invalid combinations.
- Record platform assignment feedback to improve future inference accuracy (e.g., path-to-platform mapping cache) and expose batch operations for quick remediation.
- Cover heuristics and manual overrides with automated tests to avoid regressions in platform assignment accuracy.

### Work Item 6: Hash Cache Infrastructure
- Introduce the hash cache sidecar database (`./database/rom_curator_cache.db`) keyed by absolute path + modified time → SHA-1, with invalidation when file attributes change.
- Define a cache lifecycle policy (size limits, LRU eviction or age-out schedules) and expose maintenance commands for pruning or rebuilding the cache.
- Provide migration tooling to backfill cache entries for existing `rom_file` rows without rehashing everything at once.
- Make chunk size, cache usage, and cache statistics toggles configurable through `config.json` and the `ConfigManager` interface with upfront defaults.
- Add unit tests ensuring cache hits/misses, invalidation, and maintenance routines behave deterministically.

### Work Item 7: Performance Monitoring Foundation
- Collect per-phase performance metrics (files/minute, MB/sec, average hash/scan duration) during ingestion and expose them via the session summary, log channels, and optional database tables.
- Implement lightweight instrumentation hooks early so later work items can record timing/resource metrics without rewrites; persist throughput history for ETA estimation and for the Phase 6 optimization baseline.
- Add progress estimation and ETA calculation that refines predictions as the run progresses using historical throughput captured in the database or cache.
- Seed baseline datasets (e.g., 10k and 50k file fixtures) and record discovery/hash/match throughput so later phases have reference curves.
- Ensure configuration includes thresholds for warning-level slowdowns and toggles for telemetry collection; surface warnings in the GUI and logs when thresholds are exceeded.
- Provide automated tests or profiling scripts that exercise instrumentation code paths and verify metrics serialization.

## Phase 3 – Processing Pipeline (Work Items 8–12)
### Work Item 8: Discovery & Staging Pipeline
- Traverse paths from `library_root` breadth-first, skipping ignored directories/files (`.nomedia`, `.no-roms`, system folders) and honoring glob exclusions defined up front in `config.json` and the configuration dialog.
- Insert or update rows in `file_discovery` capturing `log_id`, `root_id`, absolute/relative paths, size, modified timestamp, recursion depth, and initial `promotion_state='pending'`.
- Persist and reload per-job checkpoint files so the walker can resume after interruption or cancellation; include resume behaviour in automated tests.
- Implement incremental scan optimisations: detect unchanged directory trees via timestamp or hash caching, support quick-scan modes for new or modified content, and maintain a directory-state cache between runs.
- Respect filesystem constraints: detect and report read-only media, skip or explicitly opt-in to following symbolic links/junctions, and capture lock/permission failures so pre-flight and resilience reporting remain accurate.

### Work Item 9: Pre-flight Validation & Configuration Guardrails
- Provide a pre-flight validation report that classifies files as supported, unsupported, or requiring user action before ingestion begins.
- Estimate run duration before execution by combining discovery/hash/match throughput captured in Work Item 7. Display a phase-level breakdown (discovery, hashing, matching) plus total runtime with ±15% confidence bands.
- Surface the estimate prominently in the UI/logs using the phrasing "Processing this collection will take approximately X hours (Discovery: Y, Hashing: Z, Matching: W)."
- Calculate required disk usage (temporary extraction, final organized footprint) using configured defaults and observed archive sizes; warn when available space is below 1.5× the projected requirement.
- Surface blocking issues (encrypted archives, unknown formats, permissions, NAS/network storage latency) up front and allow the user to cancel or adjust settings before the main run.
- Validate that required `config.json` settings exist and meet schema requirements before launch; offer guided remediation for missing/invalid values inside the configuration UI.
- Detect oversize collections (>100,000 files or >2 TB) and highlight the impact on database growth, checkpoint frequency, and required cache size before continuing.
- Integrate pre-flight results into logging and session metadata for auditing; persist snapshots with the run log for later review.
- Implement automated tests covering supported/unsupported detection, configuration validation, runtime/space estimation, and cancellation pathways.

### Work Item 10: Hashing & Promotion Pipeline
- Implement chunked hashing (SHA-1 required, MD5/CRC32 when requested) that operates on disk files and streamed archive members without exhausting memory.
- Upon successful hash, upsert into `rom_file`, update the corresponding `file_discovery` row (`rom_id`, `promotion_state='hashed'`, `last_seen`), and upsert a `file_instance` row (`first_seen`, `last_seen`, `status`).
- Handle missing or moved files by marking prior `file_instance` rows as `status='missing'` when not observed in the current run.
- Leverage the hash cache to bypass redundant hashing where safe; log cache hit rates through the performance monitoring hooks.
- Add tests validating hashing accuracy, database promotion logic, cache reuse, and missing file handling.

### Work Item 11: Archive Handling & Auxiliary Asset Support
- Detect archives via the extension registry and signature probes; enumerate contents using streaming readers that handle nested archives up to the configured depth.
- Record member relationships in `archive_member`, designating primary playable entries and capturing compressed/uncompressed sizes and modification metadata.
- Implement failure handling for password-protected or corrupt archives, recording issues in `file_operation_log` and keeping `file_discovery` rows in a `promotion_state='failed'` state for operator review.
- Detect solid archives (e.g., 7z solid blocks) and fall back to controlled extraction strategies with configurable temp-storage limits (default 10 GB, configurable) and memory ceilings (default 2 GB, configurable); support split archives (.001, .002, multi-part ZIP/7Z) by reassembling or sequentially streaming segments prior to hashing.
- Trigger throttling when memory usage exceeds 80% of the configured ceiling and log the slow-down through performance instrumentation.
- Classify non-ROM assets using `rom_file.content_role` (`auxiliary`, `patch`, `save`, etc.) so they remain traceable; provide tests or fixtures covering nested archives, password handling stubs, and failure reporting.

### Work Item 12: Metadata Extraction Enhancements
- Implement optional `rom_file_metadata` storage for format-specific insights (disc metadata, internal ROM headers, etc.) with schema validation to prevent inconsistent payloads.
- Expand extractor plugins to capture metadata for priority formats while respecting configuration toggles.
- Surface extracted metadata in logs and optional UI panels for operator review.
- Provide unit tests for metadata parsers, ensuring malformed inputs are handled gracefully.

## Phase 4 – Matching & Organization (Work Items 13–16)
### Work Item 13: DAT Correlation & Ingestion Candidate Pipeline
- Implement hash-first matching between `rom_file.sha1` and `dat_entry.rom_sha1`; when successful, create/update `dat_atomic_link` with `match_type='automatic'` and confidence scores.
- For unresolved files, invoke `GameMatcher` with platform hints derived from extensions and `platform_links`; generate candidate rows in the new `ingestion_candidate` table with provenance to the current `import_log`.
- Annotate candidates with reasons/metrics and ensure `import_log` provenance is captured for auditing; prevent duplicate candidates when reprocessing the same file.
- Provide automated tests covering direct hash matches, fuzzy candidate generation, and deduplication of links.

```sql
CREATE TABLE IF NOT EXISTS ingestion_candidate (
    candidate_id INTEGER PRIMARY KEY,
    rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    dat_entry_id INTEGER REFERENCES dat_entry(dat_entry_id),
    suggested_atomic_id INTEGER REFERENCES atomic_game_unit(atomic_id),
    confidence REAL NOT NULL,
    reason TEXT,
    log_id INTEGER REFERENCES import_log(log_id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed INTEGER DEFAULT 0
);
```

### Work Item 14: Conflict Resolution Workflows
- Detect duplicate content scenarios (identical hashes in multiple locations) and surface resolution options (keep both, merge, quarantine) in the curation UI.
- Implement configurable version preference rules (e.g., prioritise Rev 2 over Rev 1) that influence automatic linking and organizer/export outcomes.
- Provide manual override workflows allowing curators to pin preferred releases/ROMs, with audit trails stored alongside `dat_atomic_link` or a companion table.
- Ensure organizer and export routines respect resolved conflicts and never revert manual decisions or version preferences; cover duplicate detection/resolution with automated tests.

### Work Item 15: Curation Workflow Updates
- Extend the curation GUI to load `ingestion_candidate` records, highlight "New from ingestion" items, and allow quick accept/reject actions.
- Respect the existing auto-link preference, only promoting high-confidence matches to `release_artifact` when auto-linking is enabled.
- Emit Qt signals when ingestion runs complete so the curation queue refreshes automatically without manual reloads.
- Cover UI interactions with automated tests or scripted Qt harnesses to ensure queue updates and filters behave as expected.

### Work Item 16: Library Organisation & Operation Logging
- Implement `FileOrganizerService` (or extend the existing organizer) to compute destination paths based on release metadata, platform links, and configurable templates defined in `config.json`.
- Define a quarantine strategy: default to moving items to `./quarantine/<log_id>/` (configurable `quarantine_root`), record provenance, and differentiate between quarantine (recoverable conflicts, permission issues, unresolved duplicates) and deletion (operator-confirmed purge).
- Record every move/copy/quarantine in `file_operation_log`, including source/destination, status, and messages for failures; generate a backup manifest per run.
- Provide automated restore tooling that reads the manifest to reinstate quarantined files or undo moves; document that quarantine remains until the operator clears it.
- Provide a dry-run preview that includes a per-file before/after table and expose "Apply Library Organization" as an explicit post-ingestion action; persist manifests alongside session logs.
- Offer an "undo last organization" command that replays the backup manifest to restore files to their prior locations.
- Include automated tests verifying dry-run output, manifest generation, undo routines, quarantine restore flows, and detection of external moves between runs.

## Phase 5 – User Experience (Work Items 17–19)
### Work Item 17: Bulk Platform Operations & Smart Defaults
- Add a bulk platform assignment workflow that groups unknown files by heuristics (extension, directory name, parent folder) and allows batch assignment with persistent learning.
- Enhance platform inference to use parent folder naming schemes, user-defined rules, and prior operator selections; persist learned mappings for future runs.
- Provide skip/whitelist controls for BIOS/system files, homebrew, or other content that should not be matched/organised like standard ROMs.
- Allow users to target ingestion to specific platforms or collections to reduce scope and processing time when desired; cover bulk actions and scoped runs with automated tests.

### Work Item 18: UI Integration & Configuration Experience
- Add "Tools → Library → Scan & Ingest Files..." to the main window, launching the ingestion dialog with progress, cancellation, and telemetry displays.
- Enhance the enhanced importer UI to display ingestion metrics (files seen, hashed, matched, pending) and run summaries, linking to per-run log files and pre/post-flight reports, including pre-flight time/space estimates.
- Extend the configuration dialog to expose archive depth limit, password dictionary path, hash chunk size, database batch sizes, organizer defaults, telemetry thresholds, and resource ceilings (`memory_limit_mb` default 2048, `temp_space_limit_gb` default 10, `throttle_trigger_percent` default 80). Ensure `ConfigManager` persists and applies these settings.
- Detect network-mounted paths (UNC shares, SMB/NFS mounts) during configuration/pre-flight and warn about reduced throughput or checkpoint tuning needs.
- Implement adaptive batching controls with memory-pressure detection and automatic back-off tied to configuration values; verify via automated GUI/service tests.

### Work Item 19: UAT Readiness Reports & Post-run Verification
- Generate a post-run verification report detailing files processed, actions taken, failures (with reasons), and any manual follow-ups required; call out time/space estimate accuracy by comparing pre-flight predictions with actual results.
- Capture and archive both pre-flight (from Work Item 9) and post-run reports with the session logs so they can be reviewed or shared post-run.
- Provide export options (HTML/CSV) for QA review and stakeholder communication; include operator acknowledgements or sign-offs in the UI and audit log when post-run issues are resolved.
- Supply automated tests that validate report content, persistence, export routines, and acknowledgement flows.

## Phase 6 – Quality & Documentation (Work Items 20–21)
### Work Item 20: Documentation & Runbook Updates
- Update `Rom Curator Database Documentation.md` with the new tables/columns, including ER diagrams or table listings where applicable.
- Refresh `README.md` and `Agents.md` to describe the ingestion workflow, prerequisites, configuration options, telemetry, and troubleshooting steps for archives/missing files.
- Provide an operator runbook outlining restart procedures, interpreting logs, reviewing pre/post-flight reports, and common remediation actions (password-protected archives, missing files, etc.).
- Maintain a configuration reference that enumerates all ingestion-related keys, defaults, and tuning guidance; add documentation linting or link-checking in CI.

### Work Item 21: Performance Optimization & Hardening
- Implement adaptive batching that tunes batch sizes based on file size distribution and system load, with user-configurable ceilings in `config.json`.
- Monitor memory, CPU, and disk I/O usage during ingestion; throttle or pause work when thresholds are exceeded, logging the adjustments through the performance monitoring framework.
- Apply targeted optimizations (parallel hashing, pipelined staging) where profiling indicates bottlenecks, ensuring changes respect the resilience guardrails from earlier phases.
- Capture before/after benchmarks to quantify throughput improvements. Establish the baseline immediately after Work Item 7 using the recorded fixtures, and require that optimizations demonstrate improvements against those baseline metrics (files/minute, MB/sec, average ETA error).
- Integrate regression tests or benchmark scripts into CI/CD where feasible so baseline drift is detected automatically.

## Continuous Testing & Configuration Governance
- Treat automated testing as a cross-cutting concern: every work item should land unit tests or integration coverage alongside implementation. Phase 3 items must also deliver integration tests that exercise multi-stage flows, and Phase 5–6 wrap up with end-to-end fixtures covering discovery through organization.
- Keep `config.json` authoritative—new keys must ship with defaults, validation, documentation, and UI controls before dependent work lands. Pre-flight validation should reject runs with missing or invalid configuration values.
- Maintain deterministic fixtures for discovery, hashing, archive handling, and matching so regression suites remain stable across environments.

## Follow-Up & Dependency Notes
- Phase ordering reflects critical dependencies: schema/logging/configuration groundwork in Phase 1 enables registry, platform inference, caching, and telemetry in Phase 2. Those, in turn, support the processing pipeline of Phase 3.
- Matching, conflict handling, and organization (Phase 4) rely on accurate discovery, hashing, and metadata capture; do not begin until earlier acceptance criteria are met.
- UX improvements and reporting (Phase 5) depend on prior telemetry and data availability, while Phase 6 hardens the solution and captures institutional knowledge for operators.
