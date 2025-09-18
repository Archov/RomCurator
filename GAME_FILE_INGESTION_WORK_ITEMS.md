# Game File Ingestion - Work Items
The following work items break down the implementation plan into actionable chunks. Each item includes concrete requirements and acceptance criteria so an AI agent (or human teammate) can verify completion objectively. Unit tests and automated checks are expected to be authored alongside each work item; regression coverage should accumulate throughout the program rather than arriving in a single dedicated task.

### Phase 1: Foundation
---
## Work Item 1: Database Foundations for Ingestion
**Requirements**
- Update `Rom Curator Database.sql` to add `file_discovery`, `archive_member`, `rom_file_metadata`, `file_operation_log`, and `ingestion_queue` tables with the columns and constraints defined in the implementation plan.
- Update existing table definitions in `Rom Curator Database.sql` to add `file_instance.first_seen`, `file_instance.last_modified`, `file_instance.status`, `release_artifact.artifact_sequence`, and `rom_file.content_role` with appropriate defaults and checks.
- Ensure foreign keys, unique indexes, and cascading rules mirror the schema defined in the plan; include backwards-compatible defaults for existing rows.
- Provide migration-safe scripts or guidance so existing deployments can apply the schema updates without data loss.

**Acceptance Criteria**
- Databases created with the updated schema file match the existing structure plus the changes outlined in the implementation plan.
- Introspection (`PRAGMA table_info` / `sqlite_master`) confirms every new column/table/index is present with the expected constraints.
- Automated smoke test (or scripted check) verifies that inserting sample records respects the new foreign keys and uniqueness constraints.

---
## Work Item 2: Logging, Error Handling & Resilience
**Requirements**
- Add dedicated logging channels (`ingestion`, `ingestion.archive`, `ingestion.organizer`) via `LoggingManager` and ensure all worker components log meaningful events from the start of the project.
- Implement granular error handling that rolls back only the active batch while persisting prior progress; failed entries should stay in `file_discovery` with diagnostic messages.
- Persist checkpoint state frequently, honor cancellation flags promptly, and surface recoverable issues (e.g., permission problems) in the session summary.
- Establish unit tests or fault-injection harnesses that exercise cancellation, checkpoint recovery, and logging paths.

**Acceptance Criteria**
- Import logs show phase transitions, per-file outcomes, and explicit warnings/errors; log viewer filters expose ingestion-specific logs.
- Force-injecting an error during processing leaves earlier work committed and records the failure details for the affected file.
- Cancelling an ingestion run mid-way produces a resumable checkpoint and user-facing notification confirming the pause; automated tests cover these behaviours.

---
## Work Item 3: Metadata Source Integration & Job Wiring
**Requirements**
- Register a `file_ingestion` entry in `metadata_source` and seed scripts so the new workflow can be triggered from both CLI and GUI contexts.
- Implement `scripts/seeders/library_ingestion.py` (or equivalent) seeder using the shared importer base classes and exposing configurable parameters via CLI flags.
- Extend `ImportWorkerThread` to launch the new script, stream logs, emit progress updates, and respect cancellation for ingestion jobs.
- Define and document new `config.json` keys (paths, batching, validation toggles) required for ingestion; update `ConfigManager` defaults and validation so settings exist before downstream work begins.
- Provide unit tests that cover CLI invocation, GUI wiring, and configuration persistence.

**Acceptance Criteria**
- Selecting the new Library Scan job in the enhanced importer launches the worker and produces log output tied to a unique `import_log` entry.
- Cancelling a running ingestion job halts work without leaving the application in an inconsistent state (subsequent runs succeed).
- Import session summary displays correct totals for files discovered, hashed, matched, and pending review.
- Configuration updates persist through `ConfigManager`, and tests validate the wiring.

### Phase 2: Core Infrastructure
---
## Work Item 4: Extension Registry & Platform Extension UI
**Requirements**
- Implement the `file_type_category`, `file_extension`, and `platform_extension` tables with CRUD helper methods seeded with sensible defaults.
- Build a PyQt management dialog to view/filter extensions, toggle activation, assign platform mappings, and import/export extension lists.
- Integrate discovery suggestions (unknown extensions encountered during scans) into the UI for quick enable/disable actions.
- Add automated UI or service-layer tests validating CRUD operations, persistence, and unknown extension handling.

**Acceptance Criteria**
- Launching the new dialog lists default extensions grouped by category and allows toggling their active state with persistence to the database.
- Assigning a new extension to a platform updates `platform_extension` and influences subsequent discovery/classification decisions.
- Encountering an unknown extension during ingestion surfaces a UI prompt that lets the operator approve, categorise, or ignore it; tests confirm database state changes.

---
## Work Item 5: Platform Detection & Assignment
**Requirements**
- Implement platform inference heuristics using extension registry hints, directory naming patterns, and optional user-defined mapping rules declared in `config.json`.
- Provide a manual platform assignment dialog that appears when inference fails or confidence is low, persisting the operator's choice for reuse.
- Validate inferred or manually assigned platforms against `platform_links` and `platform_extension` records to prevent invalid combinations.
- Record platform assignment feedback to improve future inference accuracy (e.g., path-to-platform mapping cache).
- Cover heuristics and manual overrides with unit tests to avoid regressions in platform assignment accuracy.

**Acceptance Criteria**
- Sample directories with mixed platforms result in correct platform assignments without manual intervention in the majority of cases.
- Manual platform selections update the database and influence subsequent inference runs for identical paths/hashes.
- Invalid platform assignments surface immediate validation errors and do not persist inconsistent data; automated tests cover success and failure paths.

---
## Work Item 6: Hash Cache Infrastructure
**Requirements**
- Introduce the hash cache sidecar database (`database/rom_curator_cache.db`) keyed by absolute path + modified time → SHA-1 (with invalidation when file attributes change).
- Define a cache lifecycle policy (size limits, LRU eviction or age-out schedules) and expose maintenance commands for pruning or rebuilding the cache.
- Provide migration tooling to backfill cache entries for existing `rom_file` rows without rehashing everything at once.
- Make chunk size, cache usage, and cache statistics toggles configurable through `config.json` and the `ConfigManager` interface with upfront defaults.
- Add unit tests ensuring cache hits/misses, invalidation, and maintenance routines behave deterministically.

**Acceptance Criteria**
- Cached hashes are reused on subsequent runs when files remain unchanged, shortening processing time (verified via timing/logs).
- Cache statistics report current entries, hit rates, and storage footprint; eviction and manual maintenance operations work as expected.
- Changing a file’s modified timestamp invalidates the cache entry and forces re-hashing on the next run; automated tests verify cache flows.

---
## Work Item 7: Performance Monitoring Foundation
**Requirements**
- Collect per-phase performance metrics (files/minute, MB/sec, average hash/scan duration) during ingestion and expose them via the session summary and log channels.
- Implement lightweight instrumentation hooks early so later work items can record timing/resource metrics without rewrites.
- Add progress estimation and ETA calculation that refines predictions as the run progresses using historical throughput captured in the database or cache.
- Ensure configuration includes thresholds for warning-level slowdowns and toggles for telemetry collection.
- Provide automated tests or profiling scripts that exercise instrumentation code paths and verify metrics serialization.

**Acceptance Criteria**
- Performance metrics and ETAs appear in the ingestion summary/logs, remaining within ±15% of actual completion time after warm-up.
- Resource throttling hooks or warnings fire when configured thresholds are exceeded, and tests validate the behaviour.
- Later work items can emit metrics using the shared instrumentation without additional plumbing.

### Phase 3: Processing Pipeline
---
## Work Item 8: Discovery & Staging Pipeline
**Requirements**
- Traverse paths from `library_root` breadth-first, skipping ignored directories/files (.nomedia, .no-roms, system folders) and honoring glob exclusions from `config.json`.
- Insert or update rows in `file_discovery` capturing `log_id`, `root_id`, absolute/relative paths, size, modified timestamp, recursion depth, and initial `promotion_state="pending"`.
- Persist and reload per-job checkpoint files so the walker can resume after interruption or cancellation.
- Implement incremental scan optimisations: detect unchanged directory trees via timestamp or hash caching, support quick-scan modes for new or modified content, and maintain a directory-state cache between runs.
- Validate that ignore/exclusion settings are defined in `config.json`, surfaced in the configuration UI, and documented for operators before discovery is enabled.
- Author unit tests covering ignore rules, resume-from-checkpoint behaviour, and incremental scan decision logic.

**Acceptance Criteria**
- Running the discovery stage alone populates `file_discovery` with entries for every eligible file under the configured library roots (verified by sample directory scan).
- Ignored paths never appear in `file_discovery`; updating ignore lists and re-running removes prior staged rows or marks them as skipped.
- Killing the process mid-scan and restarting resumes from the checkpoint without reprocessing already discovered directories; automated tests demonstrate checkpoint reliability.
- Incremental scan mode skips unchanged directories while still surfacing newly added or modified files in benchmark runs.

---
## Work Item 9: Pre-flight Validation & Configuration Guardrails
**Requirements**
- Provide a pre-flight validation report that classifies files as supported, unsupported, or requiring user action before ingestion begins.
- Surface blocking issues (encrypted archives, unknown formats, permissions) up front and allow the user to cancel or adjust settings before the main run.
- Validate that required `config.json` settings exist and meet schema requirements before launch; offer guided remediation for missing/invalid values.
- Integrate pre-flight results into logging and session metadata for auditing.
- Implement automated tests covering supported/unsupported detection, configuration validation, and cancellation pathways.

**Acceptance Criteria**
- Starting an ingestion job produces a pre-flight summary that highlights counts of supported/unsupported files and paths requiring attention; users can abort or continue based on the preview.
- Configuration or filesystem issues detected during pre-flight block execution until resolved and provide actionable guidance.
- QA scenarios that intentionally include unsupported formats surface warnings before processing rather than failing silently mid-run; automated tests cover these flows.

---
## Work Item 10: Hashing & Promotion Pipeline
**Requirements**
- Implement chunked hashing (SHA-1 required, MD5/CRC32 when requested) that operates on disk files and streamed archive members without exhausting memory.
- Upon successful hash, upsert into `rom_file`, update the corresponding `file_discovery` row (`rom_id`, `promotion_state="hashed"`, `last_seen`), and upsert a `file_instance` row (`first_seen`, `last_seen`, `status`).
- Handle missing or moved files by marking prior `file_instance` rows as `status="missing"` when not observed in the current run.
- Add tests validating hashing accuracy, database promotion logic, and missing file handling.

**Acceptance Criteria**
- Sample ingestion produces `rom_file` records with populated hash columns, and associated `file_instance` rows exist with accurate timestamps.
- Re-ingesting without file changes reuses cached hashes and does not duplicate rows (idempotent behaviour verified by DB queries and automated tests).
- Removing a file’s physical source results in the next scan marking the prior `file_instance` row as `status="missing"` while leaving historical data intact.

---
## Work Item 11: Archive Handling & Auxiliary Asset Support
**Requirements**
- Detect archives via the extension registry and signature probes; enumerate contents using streaming readers that handle nested archives up to the configured depth.
- Record member relationships in `archive_member`, designating primary playable entries and capturing compressed/uncompressed sizes and modification metadata.
- Implement failure handling for password-protected or corrupt archives, recording issues in `file_operation_log` and keeping `file_discovery` rows in a `promotion_state="failed"` state for operator review.
- Detect solid archives (e.g., 7z solid blocks) and fall back to controlled extraction strategies with configurable temp-storage limits.
- Support split archives (.001, .002, multi-part ZIP/7Z) by reassembling or sequentially streaming segments prior to hashing.
- Add corruption detection and partial recovery logic that skips bad members while cataloguing the remainder, surfacing remediation guidance in the session summary.
- Provide automated tests or fixtures covering nested archives, password handling stubs, and failure reporting.

**Acceptance Criteria**
- Test archives (single ROM, multi-ROM, nested archives, password-protected, solid, and split archives) yield appropriate `archive_member` rows and primary designations or actionable failure reports.
- Password-protected or corrupted archives surface clear log entries/statuses without crashing the ingestion run, and recoverable members remain catalogued.
- Non-ROM assets (docs, cues, art) are classified using `content_role="auxiliary"` (or other category) and remain traceable in the database; fixtures/tests validate coverage.

---
## Work Item 12: Metadata Extraction Enhancements
**Requirements**
- Implement optional `rom_file_metadata` storage for format-specific insights (disc metadata, internal ROM headers, etc.).
- Expand extractor plugins to capture metadata for priority formats (cartridges, discs, multi-track images) while respecting configuration toggles.
- Surface extracted metadata in logs and optional UI panels for operator review.
- Define schema and validation for metadata payloads to prevent inconsistent structures.
- Provide unit tests for metadata parsers, ensuring malformed inputs are handled gracefully.

**Acceptance Criteria**
- Metadata extraction populates sample key/value data for supported formats and persists to `rom_file_metadata`.
- Operators can inspect extracted metadata through logs or UI panels, and configuration toggles enable/disable extraction deterministically.
- Malformed metadata inputs fail gracefully with clear diagnostics; automated tests cover success and failure cases.

### Phase 4: Matching & Organization
---
## Work Item 13: DAT Correlation & Ingestion Candidate Pipeline
**Requirements**
- Implement hash-first matching between `rom_file.sha1` and `dat_entry.rom_sha1`; when successful, create/update `dat_atomic_link` with `match_type="automatic"` and confidence scores.
- For unresolved files, invoke `GameMatcher` with platform hints derived from extensions and `platform_links`; generate candidate rows in the new `ingestion_candidate` table.
- Annotate candidates with reasons/metrics and ensure `import_log` provenance is captured for auditing.
- Provide automated tests covering direct hash matches, fuzzy candidate generation, and deduplication of links.

**Acceptance Criteria**
- Known-good ROMs with matching DAT hashes are automatically linked, visible via the existing matching views.
- Lower confidence matches appear in `ingestion_candidate` with meaningful explanations and confidence scores.
- Re-processing the same file does not duplicate links or candidates; confidence updates when metadata changes are reflected accurately and covered by tests.

---
## Work Item 14: Conflict Resolution Workflows
**Requirements**
- Detect duplicate content scenarios (identical hashes in multiple locations) and surface resolution options (keep both, merge, quarantine) in the curation UI.
- Implement configurable version preference rules (e.g., prioritise Rev 2 over Rev 1) that influence automatic linking and organizer/export outcomes.
- Provide manual override workflows allowing curators to pin preferred releases/ROMs, with audit trails stored alongside `dat_atomic_link` or in a companion table.
- Ensure organizer and export routines respect resolved conflicts and never revert manual decisions or version preferences.
- Create automated tests simulating duplicate detection, resolution actions, and organizer/export interplay.

**Acceptance Criteria**
- Ingestion runs on datasets with duplicates produce actionable conflict entries that can be resolved via the curation UI.
- Version preference rules update auto-link behaviour and organizer outputs, with changes logged for traceability.
- Manual overrides persist across subsequent ingestion runs and are honoured by organizer/export processes; automated tests cover these flows.

---
## Work Item 15: Curation Workflow Updates
**Requirements**
- Extend the curation GUI to load `ingestion_candidate` records, highlight "New from ingestion" items, and allow quick accept/reject actions.
- Respect the existing auto-link preference, only promoting high-confidence matches to `release_artifact` when auto-linking is enabled.
- Emit Qt signals when ingestion runs complete so the curation queue refreshes automatically without manual reloads.
- Cover UI interactions with automated tests or scripted Qt harnesses to ensure queue updates and filters behave as expected.

**Acceptance Criteria**
- After running an ingestion job, the curation UI displays new candidates grouped or filtered by ingestion status.
- Accepting or rejecting a candidate updates the underlying tables (`dat_atomic_link`, `ingestion_candidate.processed`) and removes the item from the queue.
- Auto-link preference toggles immediately influence whether confirmed matches are created automatically during ingestion; automated tests verify the behaviour.

---
## Work Item 16: Library Organisation & Operation Logging
**Requirements**
- Implement `FileOrganizerService` (or extend the existing organizer) to compute destination paths based on release metadata, platform links, and configurable templates.
- Record every move/copy/quarantine in `file_operation_log`, including source/destination, status, and messages for failures.
- Provide a dry-run preview that includes a per-file before/after table and expose "Apply Library Organization" as an explicit post-ingestion action.
- Generate a backup manifest (original path, destination path, hash) prior to executing moves and store it with the session logs.
- Offer an "undo last organization" command that replays the backup manifest to restore files to their prior locations.
- Include automated tests verifying dry-run output, manifest generation, and undo routines.

**Acceptance Criteria**
- Running the organizer in dry-run mode produces a detailed, exportable diff of proposed moves without altering the filesystem or database.
- Executing the organizer moves files into the configured library structure, updates `file_instance` paths, and logs each operation; the backup manifest is written alongside the run log.
- Invoking the undo command after a move restores files to their previous locations and updates `file_instance`/`file_operation_log` accordingly; automated tests confirm behaviour.
- Moving files externally between runs is detected; the next organizer run logs a restore or missing status as appropriate.

---
## Work Item 17: Bulk Platform Operations & Smart Defaults
**Requirements**
- Add a bulk platform assignment workflow that groups unknown files by heuristics (extension, directory name, parent folder) and allows batch assignment.
- Enhance platform inference to use parent folder naming schemes, user-defined rules, and prior operator selections ("remember for similar files").
- Provide skip/whitelist controls for BIOS/system files, homebrew, or other content that should not be matched/organised like standard ROMs.
- Allow users to target ingestion to specific platforms or collections to reduce scope and processing time when desired.
- Create tests for bulk operations, whitelist handling, and scoped ingestion.

**Acceptance Criteria**
- Large collections with hundreds of unknown files can be resolved via batch assignments instead of individual prompts; decisions persist for future runs.
- Platform inference learns from user overrides and applies them consistently to matching paths on later scans.
- BIOS/system content flagged via skip lists remains untouched by matching, organisation, and reporting workflows.
- Operators can limit a run to selected platforms and see reduced processing time in UAT scenarios; automated tests validate scoped execution.

### Phase 5: User Experience
---
## Work Item 18: UI Integration & Configuration Experience
**Requirements**
- Add "Tools -> Library -> Scan & Ingest Files..." to the main window, launching the ingestion dialog with progress and cancellation controls.
- Enhance the enhanced importer UI to display ingestion metrics (files seen, hashed, matched, pending) and run summaries.
- Extend the configuration dialog to expose archive depth limit, password dictionary path, hash chunk size, database batch sizes, and organizer defaults; ensure `ConfigManager` persists and applies these settings.
- Implement adaptive batching for database writes and queue processing, including memory-pressure detection with automatic back-off and user-configurable ceilings.
- Cover UI additions and configuration persistence with automated tests.

**Acceptance Criteria**
- The new menu entry opens the ingestion workflow; progress and status updates stay responsive throughout a run.
- Session results panel shows accurate counts and links to the per-run log file.
- Changing configuration values updates `config.json` and alters subsequent ingestion behaviour (e.g., archive depth limit enforced, batch sizes adjusted).
- Stress tests demonstrate batching adapts to memory/CPU pressure without data loss or stalled UI updates; automated tests confirm configuration handling.

---
## Work Item 19: UAT Readiness Reports & Post-run Verification
**Requirements**
- Generate a post-run verification report detailing files processed, actions taken, failures (with reasons), and any manual follow-ups required.
- Capture and archive both pre-flight (from Work Item 9) and post-run reports with the session logs so they can be reviewed or shared post-run.
- Provide export options (HTML/CSV) for QA review and stakeholder communication.
- Incorporate operator acknowledgements or sign-offs into the UI and audit log when post-run issues are resolved.
- Supply automated tests that validate report content, persistence, and export routines.

**Acceptance Criteria**
- Post-run verification reports include success/failure totals, reasons for failures, and links to relevant logs; reports are saved and can be exported from the UI.
- QA scenarios that intentionally include unsupported formats show pre-flight warnings and post-run follow-up actions with consistent identifiers.
- Stakeholders can sign off on completed runs, with acknowledgements captured in the database; tests confirm report generation and archival.

### Phase 6: Quality & Documentation
---
## Work Item 20: Documentation & Runbook Updates
**Requirements**
- Update `Rom Curator Database Documentation.md` with the new tables/columns, including ER diagrams or table listings where applicable.
- Refresh `README.md` (and `Agents.md`) to describe the ingestion workflow, prerequisites, configuration options, and troubleshooting steps for archives/missing files.
- Provide an operator runbook outlining restart procedures, interpreting logs, and common remediation actions (password-protected archives, missing files, etc.).
- Maintain a configuration reference that enumerates all ingestion-related keys, defaults, and tuning guidance.
- Include documentation linting or link-checking in CI to prevent regressions.

**Acceptance Criteria**
- Documentation changes reviewed for accuracy and consistency with implemented features; no outdated references remain to the prior schema or legacy importer.
- New sections include screenshots or callouts where useful (e.g., extension manager dialog, ingestion summary view).
- Internal stakeholders confirm they can follow the runbook to execute an ingestion cycle and resolve the documented edge cases; documentation tests/link checks pass.

---
## Work Item 21: Performance Optimization & Hardening
**Requirements**
- Implement adaptive batching that tunes batch sizes based on file size distribution and system load, with user-configurable ceilings in `config.json`.
- Monitor memory, CPU, and disk I/O usage during ingestion; throttle or pause work when thresholds are exceeded, logging the adjustments.
- Apply targeted optimizations (parallel hashing, pipelined staging) where profiling indicates bottlenecks, ensuring changes respect the resilience guardrails from earlier phases.
- Capture before/after benchmarks to quantify throughput improvements.
- Provide automated performance regression tests or benchmark scripts integrated into CI/CD where feasible.

**Acceptance Criteria**
- Stress tests with mixed workloads show batching adapts automatically to stay within configured resource limits while maintaining throughput.
- Performance metrics and ETAs (from Work Item 7) reflect optimizations and remain accurate; throttling events are logged and observable.
- Benchmark reports demonstrate measurable improvements against the baseline established before optimization, and regression scripts protect against future slowdowns.
