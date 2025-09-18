# ROM Curator - AI Agent Brief

## Mission
- Deliver a deterministic desktop workflow that turns messy ROM collections into a curated, versioned library backed by validated DAT data and rich metadata.
- Favor reliability and repeatability: predictable database writes, resumable workflows, and clear user feedback beat experimental features.

## Current phase 
- Rapid development of Prototype/POC
- All changes are OK to be breaking and do not need to be backwards compatible or migration tools, no code is deployed, nothing needs to be preserved if it leads to a better shippable product.

## Architecture Snapshot
- **Unified GUI (`rom_curator_main.py`)**: Single PyQt5 entry point with menu routing to the importer, curation interface, platform linking dialog, and log viewer. Persists configuration through `ConfigManager`, applies `qdarkstyle`, and exposes a global status bar plus progress widget.
- **Importer (`enhanced_importer_gui.py`)**: Modern import surface that drives the seeder scripts. `ImportWorkerThread` launches the selected script per file, streams console output, tracks per-session logs via `ImportLogger`, supports cancellation, and surfaces success/failure counts.
- **Metadata & DAT ingestion (`scripts/seeders/*.py`)**: Source-specific importers (`mobygames.py`, `no_intro.py`, `tosec.py`) share `BaseImporter`; `dat_parser.py` normalizes DAT payloads and writes into the SQLite schema.
- **Matching & Curation (`scripts/seeders/matching_engine.py`, `curation_gui.py`)**: `GameMatcher` builds candidate links with title normalization, platform link awareness, and confidence scoring; the curation GUI loads the queue, supports auto-linking high confidence matches, and records manual decisions.
- **Platform Linking (`platform_linking_gui.py`)**: Provides the v1.8 linking workflow, editing `platform_links` so matching can span canonical versus DAT platform names.
- **Database (`Rom Curator Database.sql`, documentation)**: SQLite schema built around `atomic_game_unit`, `game_release`, `rom_file`, plus import logging, DAT staging tables, and v1.8 `platform_links`. Views support health checks and curation analytics.
- **Logging & Config**: `LoggingManager` centralizes application logs under `logs/`; importer sessions generate per-run files. `config.json` defines paths, logging level, and GUI sizing; directories are auto-created when `auto_create_directories` is true.

## Code Map
- `rom_curator_main.py`: Application bootstrap, menu wiring, configuration persistence, logging setup, shared progress bar.
- `enhanced_importer_gui.py`: Enhanced importer widget and window; manages sources, file selection, threaded execution, and log viewing.
- `curation_gui.py`: Manual matching UI backed by `GameMatcher`, featuring queue refresh, auto-link, and detail panes.
- `platform_linking_gui.py`: GUI to maintain canonical <-> alias platform relationships stored in `platform_links`.
- `scripts/seeders/`: Importer framework, DAT parser, and matching engine used by both GUI flows and command-line scripts.
- `Rom Curator Database Documentation.md`: Authoritative schema reference, table purpose, and migration notes.
- `data_importer_gui.py`: Legacy importer retained for reference; new work should target the enhanced importer.
- `start_rom_curator.py`: Small launcher for the main window.
- `logs/`, `seed-data/`, `seed-scripts/`: Runtime artefacts and seeding helpers; treat as data, not source.

## Implementation Status
- **Complete and stable**
  - Unified main window with working importer, curation, platform linking, and log viewer entry points.
  - Enhanced importer with per-file execution, live console feed, progress updates, cancellation, and session logging.
  - Matching engine that respects `platform_links`, exposes auto-link helpers, and feeds the curation queue.
  - Platform linking dialog editing `platform_links` records within the live database.
  - Config-driven directory management and rotating application logs.
- **Partial or stubbed**
  - `Tools > Database > Setup Matching System...` exists but is not wired to a handler yet.
  - `Tools > Database > Validate Matching...` displays a placeholder message; the validation workflow still needs implementation.
  - Matching health reports exist in SQL views, but no GUI surface consumes them yet.
  - 1G1R/romset UI referenced in documentation has not been built; only database primitives exist.
  - Legacy importer remains in the tree; migrations to the enhanced workflow should ensure parity before removal.
- **Not started / tracked in docs**
  - Export system, playlist generation, library scanning and verification, advanced curation policy editors, and cloud sync remain future work outlined in the documentation.

## Operational Guidelines for Agents
- Use `ConfigManager` for configuration access and let it create directories; do not hard-code paths.
- Log through `logging.getLogger(__name__)` or the provided logger instances; importer code must report via `ImportLogger`.
- Interact with the database using `sqlite3` with `row_factory=sqlite3.Row` when mirroring existing patterns; prefer helper methods in `GameMatcher` or importer base classes when available.
- Maintain PyQt5 conventions: keep long-running work in threads, update UI via signals, and respect the dark stylesheet.
- Keep new files ASCII and follow existing naming/style conventions; document complex logic with concise comments.

## Reference Documents
- `README.md`: End-user flow, menus, and configuration expectations.
- `Rom Curator Database Documentation.md`: Detailed schema, migrations, and view inventory.
- `dat_validation_queries.sql`: Ad-hoc SQL checks backing the validation roadmap.
- `requirements.txt`: Dependency list for setting up the environment.
