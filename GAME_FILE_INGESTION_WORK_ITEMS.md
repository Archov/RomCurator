# Game File Ingestion â€“ Work Items
The following work items break down the implementation plan into actionable chunks. Each item includes concrete requirements and acceptance criteria so an AI agent (or human teammate) can verify completion objectively.
---
## Work Item 1: Database Foundations for Ingestion
**Requirements**
- Update `Rom Curator Database.sql` to add `file_discovery`, `archive_member`, `rom_file_metadata`, `file_operation_log`, and `ingestion_queue` tables with the columns and constraints defined in the implementation plan.
- Update existing table definitions in `Rom Curator Database.sql` to add `file_instance.first_seen`, `file_instance.last_modified`, `file_instance.status`, `release_artifact.artifact_sequence`, and `rom_file.content_role` with appropriate defaults and checks.
- Ensure foreign keys, unique indexes, and cascading rules mirror the schema defined in the plan; include backwards-compatible defaults for existing rows.

**Acceptance Criteria**
- Databases created with the newly produced schema file are in line with the existing structure plus the changes outlined in the implementation plan.
- Introspection (`PRAGMA table_info` / `sqlite_master`) confirms every new column/table/index is present with the expected constraints.
- Automated smoke test (or scripted check) verifies that inserting sample records respects the new foreign keys and uniqueness constraints.

---
## Work Item 2: Metadata Source Integration & Job Wiring
**Requirements**
- Register a `file_ingestion` entry in `metadata_source` and seed scripts so the new workflow can be triggered from both CLI and GUI contexts.
- Implement `scripts/seeders/library_ingestion.py` (or equivalent) seeder using the shared importer base classes and exposing configurable parameters via CLI flags.
- Extend `ImportWorkerThread` to launch the new script, stream logs, emit progress updates, and respect cancellation for ingestion jobs.

**Acceptance Criteria**
- Selecting the new Library Scan job in the enhanced importer launches the worker and produces log output tied to a unique `import_log` entry.
- Cancelling a running ingestion job halts work without leaving the application in an inconsistent state (subsequent runs succeed).
- Import session summary displays correct totals for files discovered, hashed, matched, and pending review.

---
## Work Item 3: Discovery & Staging Pipeline
**Requirements**
- Traverse paths from `library_root` breadth-first, skipping ignored directories/files (.nomedia, .no-roms, system folders) and honoring glob exclusions from `config.json`.
- Insert or update rows in `file_discovery` capturing `log_id`, `root_id`, absolute/relative paths, size, modified timestamp, recursion depth, and initial `promotion_state="pending"`.
- Persist and reload per-job checkpoint files so the walker can resume after interruption or cancellation.

**Acceptance Criteria**
- Running the discovery stage alone populates `file_discovery` with entries for every eligible file under the configured library roots (verified by sample directory scan).
- Ignored paths never appear in `file_discovery`; updating ignore lists and re-running removes prior staged rows or marks them as skipped.
- Killing the process mid-scan and restarting resumes from the checkpoint without reprocessing already discovered directories.

---
## Work Item 4: Hashing & Promotion Pipeline
**Requirements**
- Implement chunked hashing (SHA-1 required, MD5/CRC32 when requested) that operates on disk files and streamed archive members without exhausting memory.
- Upon successful hash, upsert into `rom_file`, update the corresponding `file_discovery` row (`rom_id`, `promotion_state="hashed"`, `last_seen`), and upsert a `file_instance` row (`first_seen`, `last_seen`, `status`).
- Handle missing or moved files by marking prior `file_instance` rows as `status="missing"` when not observed in the current run.

**Acceptance Criteria**
- Sample ingestion produces `rom_file` records with populated hash columns, and associated `file_instance` rows exist with accurate timestamps.
- Re-ingesting without file changes reuses cached hashes and does not duplicate rows (idempotent behaviour verified by DB queries).
- Removing a file from disk results in the next scan marking the prior `file_instance` row as `status="missing"` while leaving historical data intact.

---
## Work Item 5: Archive Handling & Auxiliary Asset Support
**Requirements**
- Detect archives via the extension registry and signature probes; enumerate contents using streaming readers that handle nested archives up to the configured depth.
- Record member relationships in , designating primary playable entries and capturing compressed/uncompressed sizes and modification metadata.
- Implement failure handling for password-protected or corrupt archives, recording issues in  and keeping  rows in a  state for operator review.
- Detect solid archives (e.g., 7z solid blocks) and fall back to controlled extraction strategies with configurable temp-storage limits.
- Support split archives (.001, .002, multi-part ZIP/7Z) by reassembling or sequentially streaming segments prior to hashing.
- Add corruption detection and partial recovery logic that skips bad members while cataloguing the remainder, surfacing remediation guidance in the session summary.

**Acceptance Criteria**
- Test archives (single ROM, multi-ROM, nested archives, password-protected, solid, and split archives) yield appropriate  rows and primary designations or actionable failure reports.
- Password-protected or corrupted archives surface clear log entries/statuses without crashing the ingestion run, and recoverable members remain catalogued.
- Non-ROM assets (docs, cues, art) are classified using  (or other category) and remain traceable in the database.

---
## Work Item 6: Extension Registry & Platform Extension UI
**Requirements**
- Implement the `file_type_category`, `file_extension`, and `platform_extension` tables with CRUD helper methods seeded with sensible defaults.
- Build a PyQt management dialog to view/filter extensions, toggle activation, assign platform mappings, and import/export extension lists.
- Integrate discovery suggestions (unknown extensions encountered during scans) into the UI for quick enable/disable actions.

**Acceptance Criteria**
- Launching the new dialog lists default extensions grouped by category and allows toggling their active state with persistence to the database.
- Assigning a new extension to a platform updates `platform_extension` and influences subsequent discovery/classification decisions.
- Encountering an unknown extension during ingestion surfaces a UI prompt that lets the operator approve, categorise, or ignore it.

---
## Work Item 7: Metadata Extraction & Hash Cache
**Requirements**
- Implement optional  storage for format-specific insights (disc metadata, internal ROM headers, etc.).
- Introduce the hash cache sidecar database () keyed by absolute path + modified time â†’ SHA-1 (with invalidation when file attributes change).
- Define a cache lifecycle policy (size limits, LRU eviction or age-out schedules) and expose maintenance commands for pruning or rebuilding the cache.
- Provide migration tooling to backfill cache entries for existing  rows without rehashing everything at once.
- Make chunk size, cache usage, cache statistics, and metadata extraction toggles configurable through  and the  interface.

**Acceptance Criteria**
- Cached hashes are reused on subsequent runs when files remain unchanged, shortening processing time (verified via timing/logs).
- Cache statistics report current entries, hit rates, and storage footprint; eviction and manual maintenance operations work as expected.
- Metadata extraction populates sample key/value data for supported formats and persists to .
- Changing a fileâ€™s modified timestamp invalidates the cache entry and forces re-hashing on the next run.

---
## Work Item 8: DAT Correlation & Ingestion Candidate Pipeline
**Requirements**
- Implement hash-first matching between `rom_file.sha1` and `dat_entry.rom_sha1`; when successful, create/update `dat_atomic_link` with `match_type="automatic"` and confidence scores.
- For unresolved files, invoke `GameMatcher` with platform hints derived from extensions and `platform_links`; generate candidate rows in the new `ingestion_candidate` table.
- Annotate candidates with reasons/metrics and ensure `import_log` provenance is captured for auditing.

**Acceptance Criteria**
- Known-good ROMs with matching DAT hashes are automatically linked, visible via the existing matching views.
- Lower confidence matches appear in `ingestion_candidate` with meaningful explanations and confidence scores.
- Re-processing the same file does not duplicate links or candidates; confidence updates when metadata changes are reflected accurately.

---
## Work Item 9: Curation Workflow Updates
**Requirements**
- Extend the curation GUI to load `ingestion_candidate` records, highlight â€œNew from ingestionâ€ items, and allow quick accept/reject actions.
- Respect the existing auto-link preference, only promoting high-confidence matches to `release_artifact` when auto-linking is enabled.
- Emit Qt signals when ingestion runs complete so the curation queue refreshes automatically without manual reloads.

**Acceptance Criteria**
- After running an ingestion job, the curation UI displays new candidates grouped or filtered by ingestion status.
- Accepting or rejecting a candidate updates the underlying tables (`dat_atomic_link`, `ingestion_candidate.processed`) and removes the item from the queue.
- Auto-link preference toggles immediately influence whether confirmed matches are created automatically during ingestion.

---
## Work Item 10: Library Organisation & Operation Logging
**Requirements**
- Implement `FileOrganizerService` (or extend the existing organizer) to compute destination paths based on release metadata, platform links, and configurable templates.
- Record every move/copy/quarantine in `file_operation_log`, including source/destination, status, and messages for failures.
- Provide a dry-run preview summarising planned operations and expose â€œApply Library Organizationâ€ as an explicit post-ingestion action.

**Acceptance Criteria**
- Running the organizer in dry-run mode produces a detailed preview without altering the filesystem or database.
- Executing the organizer moves files into the configured library structure, updates `file_instance` paths, and logs each operation.
- Moving files externally between runs is detected; the next organizer run logs a restore or missing status as appropriate.

---
## Work Item 11: Logging, Error Handling & Resilience
**Requirements**
- Add dedicated logging channels (`ingestion`, `ingestion.archive`, `ingestion.organizer`) via `LoggingManager` and ensure all worker components log meaningful events.
- Implement granular error handling that rolls back only the active batch while persisting prior progress; failed entries should stay in `file_discovery` with diagnostic messages.
- Persist checkpoint state frequently, honor cancellation flags promptly, and surface recoverable issues (e.g., permission problems) in the session summary.

**Acceptance Criteria**
- Import logs show phase transitions, per-file outcomes, and explicit warnings/errors; log viewer filters expose ingestion-specific logs.
- Force-injecting an error during processing leaves earlier work committed and records the failure details for the affected file.
- Cancelling an ingestion run mid-way produces a resumable checkpoint and user-facing notification confirming the pause.

---
## Work Item 12: UI Integration & Configuration Enhancements
**Requirements**
- Add â€œTools â†’ Library â†’ Scan & Ingest Filesâ€¦â€ to the main window, launching the ingestion dialog with progress and cancellation controls.
- Enhance the enhanced importer UI to display ingestion metrics (files seen, hashed, matched, pending) and run summaries.
- Extend the configuration dialog to expose archive depth limit, password dictionary path, hash chunk size, and organizer defaults; ensure `ConfigManager` persists and applies these settings.

**Acceptance Criteria**
- The new menu entry opens the ingestion workflow; progress and status updates stay responsive throughout a run.
- Session results panel shows accurate counts and links to the per-run log file.
- Changing configuration values updates `config.json` and alters subsequent ingestion behaviour (e.g., archive depth limit enforced).

---
## Work Item 13: Automated Testing & Fixtures
**Requirements**
- Create unit tests covering hashing utilities, archive enumeration, extension classification, database promotion logic, and matching pipelines.
- Prepare integration test fixtures (sample ROMs, archives, password-protected archives, DAT files) and automated end-to-end tests that run ingestion against them.
- Integrate the new tests into CI scripts and document how to execute them locally.

**Acceptance Criteria**
- Test suite passes locally and in CI, exercising success and failure paths for ingestion and matching.
- Fixtures reside in a dedicated test data folder with clear licensing/usage notes and do not bloat the repository unnecessarily.
- Regression tests detect intentional failures (e.g., corrupted archive) and assert that the system responds with the documented statuses.

---
## Work Item 14: Documentation & Runbook Updates
**Requirements**
- Update `Rom Curator Database Documentation.md` with the new tables/columns, including ER diagrams or table listings where applicable.
- Refresh `README.md` (and `Agents.md`) to describe the ingestion workflow, prerequisites, configuration options, and troubleshooting steps for archives/missing files.
- Provide an operator runbook outlining restart procedures, interpreting logs, and common remediation actions (password-protected archives, missing files, etc.).

**Acceptance Criteria**
- Documentation changes reviewed for accuracy and consistency with implemented features; no outdated references remain to the prior schema or legacy importer.
- New sections include screenshots or callouts where useful (e.g., extension manager dialog, ingestion summary view).
- Internal stakeholders confirm they can follow the runbook to execute an ingestion cycle and resolve the documented edge cases.