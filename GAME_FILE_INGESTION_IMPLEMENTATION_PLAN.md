# ROM Curator: Game File Ingestion Implementation Plan

## Overview & Goals
- Deliver a deterministic, resumable workflow that transforms loose files into `rom_file` records linked to releases through `release_artifact`, feeding the existing curation and organization surfaces.
- Comply with existing architecture: `ImportWorkerThread` for background execution, `GameMatcher` for DAT alignment, `platform_links` for cross-platform resolution, and the curation and importer GUIs for user feedback.
- Maintain a trustworthy library structure while keeping imports idempotent and observable through the logging and configuration systems already in place.

## End-to-End Workflow Summary
1. User launches **Tools → Library → Scan & Ingest Files…** (new) from `rom_curator_main.py`; the PyQt dialog uses `ConfigManager` paths and dispatches an ingestion job through `enhanced_importer_gui.ImportWorkerThread`.
2. The worker records a `file_ingestion` run in `import_log`, resolves active `library_root` entries, and performs resumable recursive discovery, updating `file_instance` for everything seen.
3. Each discovered file is classified (extension and header checks), hashed in a streaming fashion, and either linked to an existing `rom_file` or inserted as a new row.
4. Archives are expanded virtually: contents are enumerated, hashed, and registered as child `rom_file`s without permanently unpacking unless policy requires it; new `archive_member` records preserve container relationships.
5. For new or changed hashes, the job attempts deterministic DAT matching using `dat_entry` (hash first, then normalized metadata) and `GameMatcher` with `platform_links`. Results populate `dat_atomic_link` and enqueue unresolved items for curation.
6. On completion the job writes summary metrics to the import log, emits progress/status updates to the GUI, and (optionally) triggers folder organization moves governed by configured rules and tracked in `file_operation_log`.

## Stage 1 – Scan Orchestration & Job Tracking
- Add a new `metadata_source` row named `file_ingestion` that points to a dedicated seeder script (e.g., `scripts/seeders/library_ingestion.py`). The script is invoked by the enhanced importer just like the existing DAT/Moby workers.
- Use `import_log` to capture job lifecycle (running/completed/failed). Store aggregate counts (files seen, hashes computed, archives expanded) in `records_processed` and a JSON summary string in `notes` for later reporting.
- Persist a checkpoint file per job under `logs/ingestion/` to allow resume after interruption; the worker reads pending paths from this checkpoint before beginning a fresh walk.
- Respect cancellation requests from the GUI by periodically checking the worker’s cancellation flag; commit intermediate results to keep the run restartable.

## Stage 2 – Discovery & Inventory Updates
### Directory Scanning
- Use paths from `library_root` (relative paths resolved via `ConfigManager`) and perform breadth-first traversal to limit deep recursion memory pressure.
- Skip hidden/system folders, respect `.nomedia`, `.no-roms`, and user-specified ignore globs persisted in `config.json`.
- Record raw file observations in an in-memory queue before hashing to separate IO from CPU work. Batch database writes via transactions of ~250 records to reduce commit overhead.

### `file_instance` Maintenance
- For each observed file, compute the relative path to its root and merge the metadata into a staging row in `file_discovery`. This table buffers discovery data without requiring a `rom_id`, capturing `root_id`, absolute and relative paths, size, modified time, depth, and the active `log_id`.
- Once hashing resolves the file's content, update the staged row with the resulting `rom_id`, mark its promotion state, and then upsert into `file_instance`. Rows that fail hashing remain staged so the worker can retry or surface them to the user.
- Extend the schema with first/last seen tracking on `file_instance` so promoted records retain temporal history:
  ```sql
  ALTER TABLE file_instance ADD COLUMN first_seen TEXT;
  ALTER TABLE file_instance ADD COLUMN last_modified TEXT;
  ALTER TABLE file_instance ADD COLUMN status TEXT DEFAULT 'present' CHECK (status IN ('present','missing','quarantined'));
  ```
- When a file disappears in a later run, mark `status='missing'` on the existing `file_instance` row (during the promotion/reconciliation sweep) so the health views can surface rot without deleting historical information.

## Stage 3 – Classification & Archive Handling
### Extension Registry
- Introduce an extension registry that the GUI can manage:
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
- Ship defaults for known ROM, disc, archive, save, patch, and playlist extensions, and expose them through a PyQt management dialog.

### Archive & Container Strategy
- Identify archives via the extension registry and confirm using `libarchive`/`zipfile` signature headers to avoid false positives.
- For each archive, enumerate members without extracting the entire file: stream entries through `libarchive.public.memory_reader` to compute hashes chunk by chunk, spilling to a temp directory under `ConfigManager.get_temp_path()` when >128 MB.
- Handle nested archives by pushing discovered archive entries onto the same processing queue, tracking depth with a guard (e.g., max depth 3) to prevent infinite loops.
- Password-protected archives: attempt configured default passwords; if none succeed, record the failure in `file_operation_log` with status `password_required`, mark the `rom_file` as pending, and surface the issue in the importer summary.
- Non-ROM auxiliaries (readme, nfo, cue, cover art) inherit classification from the extension registry. Create `rom_file` rows so they remain traceable but flag them as auxiliary via a new column (`rom_file.content_role`).
  ```sql
  ALTER TABLE rom_file ADD COLUMN content_role TEXT DEFAULT 'rom' CHECK (content_role IN ('rom','disc','patch','auxiliary','save','playlist'));
  ```

### Archive Membership Tracking
- Preserve container relationships with a dedicated table:
  ```sql
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
  ```
- Mark the preferred playable asset for single-ROM archives via `is_primary` so UI components can pick the right file without re-scanning the container.

## Stage 4 – Hashing & Metadata Extraction
- Hash everything with streaming SHA‑1; compute MD5/CRC32 when the file is <1 GB or when a DAT requires it. Respect chunk sizes from `config.json` (default 32 MB) to control memory pressure.
- Populate `rom_file.sha1`, `md5`, `crc32`, `size_bytes`, and `filename` (basename only). Update `content_role` and maintain `rom_file` rows even for auxiliary assets to keep the library complete.
- Pull format-specific data where possible:
  - Disc images: probe cue/bin pairs, CHD headers, and embed disc count information.
  - Cartridge ROMs: extract internal headers (title, region) where safe.
- Store extracted metadata in a new table keyed off `rom_file` when it is not already modeled elsewhere:
  ```sql
  CREATE TABLE IF NOT EXISTS rom_file_metadata (
      rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
      metadata_key TEXT NOT NULL,
      metadata_value TEXT NOT NULL,
      PRIMARY KEY (rom_id, metadata_key)
  );
  ```
- After hashing, resolve or insert the corresponding `rom_file` row, update the matching `file_discovery` entry with `rom_id` and `promotion_state='hashed'`, and upsert into `file_instance` within the same transaction to keep discovery, hashing, and location tracking in sync.
- Cache hash results in a lightweight SQLite sidecar (`database/rom_curator_cache.db`) to bypass re-hashing unchanged files between runs; store path + modified time → sha1 mapping.

## Stage 5 – Database Integration & Schema Alignment
### Existing Entities Leveraged
- `rom_file`: canonical store for unique content hashes; now extended with `content_role`.
- `release_artifact`: link curated releases to `rom_file` IDs. Use `artifact_type='rom'|'disc'|'patch'` and add an optional ordering column for multi-disc sequencing:
  ```sql
  ALTER TABLE release_artifact ADD COLUMN artifact_sequence INTEGER;
  ```
- `file_instance`: track physical locations per root; now enriched with first/last seen and status.
- `dat_entry` + `dat_entry_metadata`: already contain normalized metadata (`base_title`, `region_normalized`) needed for matching.
- `dat_atomic_link`: persists linkage decisions (`match_type`, `confidence`). Automatic matches from ingestion use `match_type='automatic'` with annotated confidence.

### New Supporting Tables (beyond registry/membership)
- `file_discovery` buffers raw scan observations until a `rom_id` is known, allowing ingestion to resume without violating `file_instance` foreign keys:
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
  ```
- `file_operation_log` to capture moves, renames, quarantines, and culls for auditing:
  ```sql
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
  ```
- `ingestion_queue` (ephemeral table) to coordinate deferred hashing tasks for large files or nested archives if we need to throttle work across multiple threads:
  ```sql
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
  This table can be truncated after a successful run; it doubles as a resume point if the app crashes mid-scan.

## Stage 6 – DAT Correlation & GameMatcher Integration
- Hash-first: attempt to resolve every new `rom_file.sha1` against `dat_entry.rom_sha1`. If a match exists, link to the corresponding `game_release` via existing seed data (No-Intro, TOSEC) and record the association in `dat_atomic_link` by pulling the related `atomic_id`.
- Metadata fallback: when hashes do not match, use `GameMatcher` to score candidates. Feed it the normalized title derived from the file name or extracted header and supply platform candidates gathered from `library_root` hints plus the extension registry; pass these into `GameMatcher.find_all_potential_matches()`.
- Use `platform_links` to broaden search across alias platforms automatically; persist matches meeting the confidence threshold (>=0.85) as `match_type='automatic'`. Lower confidence results (<0.85) are stored as suggestions in a new `ingestion_candidate` table consumed by the curation GUI:
  ```sql
  CREATE TABLE IF NOT EXISTS ingestion_candidate (
      candidate_id INTEGER PRIMARY KEY,
      rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
      dat_entry_id INTEGER REFERENCES dat_entry(dat_entry_id),
      suggested_atomic_id INTEGER REFERENCES atomic_game_unit(atomic_id),
      confidence REAL NOT NULL,
      reason TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      processed INTEGER DEFAULT 0
  );
  ```
- Pipe confirmed matches into the curation subsystem: automatic matches update `dat_atomic_link` and call existing helper functions to enqueue the pairing for confirmation in `curation_gui` (high-confidence auto-accept) or manual review (lower confidence via `ingestion_candidate`).
- Maintain provenance by storing the originating `import_log.log_id` in each new record (add `log_id` columns to supporting tables where helpful) so analysts can trace issues back to the specific run.

## Stage 7 – Curation, Auto-Link, and Library Organization
- After matching, derive actionable items:
  - **Auto-link:** For confidence ≥0.95, immediately insert or update `release_artifact` records linking the `rom_file` to the `game_release` surfaced by DAT metadata.
  - **Curation queue:** For other cases, insert into `ingestion_candidate` and refresh the queue shown in `curation_gui`. Leverage Qt signals to notify the GUI when a new ingestion run finishes so the queue refreshes automatically.
- Generate per-run summaries (new matches, duplicates, orphaned files) and expose them via the log viewer so operators can confirm outcomes.
- Respect the existing auto-link toggle inside the curation GUI; ingestion should honor the user’s "auto-link high confidence" preference and only write `release_artifact` rows when the preference allows.

## Stage 8 – File Movement & Library Structure
- Adopt a two-phase policy: scanning is non-destructive; organization runs when the user chooses "Apply Library Organization" from the importer completion dialog.
- Movement strategy:
  - Only relocate files that are linked to a curated release (`release_artifact` exists) and pass integrity checks (hash matches DAT entry).
  - Determine destination paths using the North Star folder template (platform/region/title) defined in config; generate moves via `FileOrganizerService` that consumes `release_artifact` and `platform_links` data.
  - Record every move in `file_operation_log` (`operation_type='move'`) and update `file_instance.relative_path` accordingly in the same transaction.
- Detect external moves: during scan, when a `rom_file` hash is found under a different path, insert a new `file_instance` row and mark the old one `status='missing'`; create a `file_operation_log` entry with `operation_type='restore'` if auto-healed by the organizer.
- Provide a dry-run option in the GUI to preview the move list before committing changes.

## Stage 9 – Logging, Error Handling, and Resiliency
- Use `LoggingManager` channels (`ingestion`, `ingestion.archive`, `ingestion.organizer`) so logs surface in the existing log viewer. Include archive depth, hashing duration, and failures.
- On exceptions, roll back only the current batch while leaving earlier work committed; flag the job as `failed` in `import_log` and include the exception summary in `notes`.
- Retain partially processed archives by marking associated `ingestion_queue` records `status='error'`; the next run can pick them up.
- Provide user feedback through the GUI progress bar (files scanned vs total) and a message area listing blocked archives (password, corruption) or unexpectedly large files that were skipped based on size limits.

## Stage 10 – User Interface Integration
- **Importer GUI (`enhanced_importer_gui.py`):**
  - Add a "Library Scan" source entry using the new metadata source. The UI should reuse the existing per-run log viewer and cancellation controls.
  - Surface summary metrics (files inserted, matched, pending review) in the session results panel.
- **Main Window (`rom_curator_main.py`):**
  - Wire `Tools → Database → Validate Matching…` to launch the ingestion-aware validation dialog, showing unmatched `rom_file`s and stale `file_instance` rows. This dialog can reuse the importer log output for transparency.
- **Curation GUI (`curation_gui.py`):**
  - Subscribe to ingestion completion signals so the queue refreshes.
  - Add filters to show "New from ingestion" items coming from `ingestion_candidate`.
- **Platform Linking (`platform_linking_gui.py`):**
  - Display archive-driven platform discoveries (e.g., when an unknown extension is associated with a platform) so curators can confirm or adjust mappings.
- **Config Dialog:** add controls for archive depth limit, password dictionary path, hash chunk size, and organizer dry-run default.

## Stage 11 – Testing & Validation
- **Unit tests:** hashing utilities, archive enumeration (including nested cases), file classification, schema helpers for new tables, `FileOrganizerService` move calculations.
- **Integration tests:** run ingestion against seeded fixture directories representing mixed content (ROMs, archives, password-protected files, non-ROM extras). Validate database side effects, DAT linkage, and curation queue population.
- **Performance tests:** benchmark large directory scans using real-world directory sizes; ensure the job can resume after interruption by deleting the worker mid-run and re-launching it.
- **Manual QA:** verify GUI interactions (start/cancel/resume), ensure logs surface correctly, and confirm that organizer dry runs produce the expected move manifests.

## Implementation Phases
1. **Foundation (Schema & Services)**
   - Apply migrations for new/altered tables and columns.
   - Implement ingestion worker core (scanning, hashing, `rom_file` upsert, archive handling, caching).
   - Build extension registry defaults and management dialog.
2. **Matching & UI Wiring**
   - Integrate `GameMatcher` and DAT correlation logic, populate `dat_atomic_link`/`ingestion_candidate`.
   - Update `enhanced_importer_gui`, `rom_curator_main`, and `curation_gui` to expose the workflow and review surfaces.
   - Implement organizer dry-run view and file operation logging.
3. **Polish & Resilience**
   - Add resume support, cancellation handling, and detailed logging.
   - Optimize batching, add configuration hooks, finalize automated tests, and document runbooks in `README.md` / `Agents.md`.

## Documentation & Follow-Up
- Update `Rom Curator Database Documentation.md` with the new/altered tables and workflow diagrams.
- Extend `README.md` with user-facing instructions covering library scans, archive handling expectations, and organizer behavior.
- Capture operational playbooks in `Agents.md`, including guidance on resolving password-protected archives, handling missing files, and interpreting ingestion reports.
