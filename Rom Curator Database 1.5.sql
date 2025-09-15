-- =============================================================================
-- ATOMIC GAME DATABASE SCHEMA v1.5 (Importer Path)
--
-- Author:      Project Contributor
-- Created:     2025-09-12
-- Description: This version enhances the `metadata_source` table to include a
--              path to the associated importer script. This makes the system
--              more robust and self-contained by removing the need for an
--              external configuration file to link sources to their parsers.
--              SQLite Compatible.
-- =============================================================================

-- PRAGMA foreign_keys = ON; -- Enable foreign key support in SQLite

-- =============================================================================
-- SECTION 1: CORE GOVERNANCE & METADATA
-- =============================================================================

CREATE TABLE IF NOT EXISTS company (
  company_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS company_alias_group (
  alias_group_id INTEGER PRIMARY KEY,
  canonical_company_id INTEGER NOT NULL REFERENCES company(company_id)
);

CREATE TABLE IF NOT EXISTS company_alias (
  alias_group_id INTEGER NOT NULL REFERENCES company_alias_group(alias_group_id),
  name TEXT NOT NULL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES company(company_id)
);

CREATE TABLE IF NOT EXISTS genre (
  genre_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS platform (
  platform_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS region (
  region_code TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS atomic_game_unit (
  atomic_id INTEGER PRIMARY KEY,
  canonical_title TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS atomic_core_metadata (
    atomic_id INTEGER PRIMARY KEY REFERENCES atomic_game_unit(atomic_id) ON DELETE CASCADE,
    log_id INTEGER REFERENCES import_log(log_id),
    description TEXT,
    player_count TEXT,
    release_date TEXT
);

CREATE TABLE IF NOT EXISTS atomic_metadata_extension (
    metadata_id INTEGER PRIMARY KEY,
    atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id) ON DELETE CASCADE,
    log_id INTEGER REFERENCES import_log(log_id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(atomic_id, key)
);


-- =============================================================================
-- SECTION 2: RELEASE & ARTIFACT MODEL
-- =============================================================================

CREATE TABLE IF NOT EXISTS game_release (
  release_id INTEGER PRIMARY KEY,
  atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id),
  platform_id INTEGER NOT NULL REFERENCES platform(platform_id),
  release_title TEXT NOT NULL,
  edition TEXT NOT NULL DEFAULT '',
  product_code TEXT NOT NULL DEFAULT '',
  UNIQUE(atomic_id, platform_id, release_title, edition, product_code)
);

CREATE TABLE IF NOT EXISTS release_developer (
  release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  company_id INTEGER NOT NULL REFERENCES company(company_id),
  PRIMARY KEY (release_id, company_id)
);

CREATE TABLE IF NOT EXISTS release_publisher (
  release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  company_id INTEGER NOT NULL REFERENCES company(company_id),
  PRIMARY KEY (release_id, company_id)
);

CREATE TABLE IF NOT EXISTS release_genre (
  release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  genre_id INTEGER NOT NULL REFERENCES genre(genre_id),
  PRIMARY KEY (release_id, genre_id)
);

CREATE TABLE IF NOT EXISTS release_region (
  release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  region_code TEXT NOT NULL REFERENCES region(region_code),
  PRIMARY KEY (release_id, region_code)
);

CREATE TABLE IF NOT EXISTS rom_file (
  rom_id INTEGER PRIMARY KEY,
  sha1 TEXT NOT NULL UNIQUE,
  md5 TEXT,
  crc32 TEXT,
  size_bytes INTEGER,
  filename TEXT
);

CREATE TABLE IF NOT EXISTS release_artifact (
  artifact_id INTEGER PRIMARY KEY,
  release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id),
  artifact_type TEXT NOT NULL DEFAULT 'rom' CHECK (artifact_type IN ('rom', 'disc', 'patch')),
  UNIQUE(release_id, rom_id)
);


-- =============================================================================
-- SECTION 3: IMPORT & VALIDATION MODEL
-- =============================================================================

CREATE TABLE IF NOT EXISTS metadata_source (
    source_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    -- Path to the python script that can parse this source's files.
    -- e.g., 'scripts/seeders/1_import_dat_files.py'
    importer_script TEXT
);

-- This table is the single source of truth for all file import events.
CREATE TABLE IF NOT EXISTS import_log (
    log_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES metadata_source(source_id),
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL, -- SHA1 hash of the imported file for idempotency
    import_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    records_processed INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(file_hash) -- Prevent the exact same file from being processed twice
);

-- dat_entry now links directly to the import_log event
CREATE TABLE IF NOT EXISTS dat_entry (
  dat_entry_id INTEGER PRIMARY KEY,
  log_id INTEGER NOT NULL REFERENCES import_log(log_id),
  platform_id INTEGER NOT NULL REFERENCES platform(platform_id), -- Stored for context
  release_title TEXT NOT NULL,
  rom_sha1 TEXT NOT NULL,
  is_clone BOOLEAN NOT NULL DEFAULT 0,
  clone_of TEXT
);

-- =============================================================================
-- SECTION 4: OPERATIONAL MODEL - FILE & EXPORT MANAGEMENT
-- =============================================================================

CREATE TABLE IF NOT EXISTS library_root (
  root_id INTEGER PRIMARY KEY,
  root_path TEXT NOT NULL UNIQUE,
  label TEXT
);

CREATE TABLE IF NOT EXISTS file_instance (
  instance_id INTEGER PRIMARY KEY,
  root_id INTEGER NOT NULL REFERENCES library_root(root_id),
  rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id),
  relative_path TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  UNIQUE(root_id, rom_id, relative_path)
);

CREATE TABLE IF NOT EXISTS selection_policy (
  policy_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  region_order TEXT NOT NULL,
  language_order TEXT,
  video_standard_order TEXT DEFAULT 'NTSC,PAL',
  exclude_clones BOOLEAN DEFAULT 1,
  exclude_unverified BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS romset_version (
  version_id INTEGER PRIMARY KEY,
  policy_id INTEGER NOT NULL REFERENCES selection_policy(policy_id),
  name TEXT NOT NULL,
  version_tag TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(name, version_tag)
);

CREATE TABLE IF NOT EXISTS romset_member (
  version_id INTEGER NOT NULL REFERENCES romset_version(version_id),
  atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id),
  chosen_release_id INTEGER NOT NULL REFERENCES game_release(release_id),
  chosen_rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id),
  PRIMARY KEY (version_id, atomic_id)
);

CREATE TABLE IF NOT EXISTS playlist (
  playlist_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS playlist_item (
  playlist_id INTEGER NOT NULL REFERENCES playlist(playlist_id),
  atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id),
  display_order INTEGER NOT NULL,
  PRIMARY KEY (playlist_id, atomic_id)
);

CREATE TABLE IF NOT EXISTS target_device (
  device_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS export_profile (
  profile_id INTEGER PRIMARY KEY,
  device_id INTEGER NOT NULL REFERENCES target_device(device_id),
  name TEXT NOT NULL UNIQUE,
  path_template TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS export_run (
  run_id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES export_profile(profile_id),
  version_id INTEGER NOT NULL REFERENCES romset_version(version_id),
  export_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT
);


-- =============================================================================
-- SECTION 5: INDEXES
-- =============================================================================

-- Foreign Key Indexes
CREATE INDEX IF NOT EXISTS idx_game_release_atomic_id ON game_release(atomic_id);
CREATE INDEX IF NOT EXISTS idx_dat_entry_log_id ON dat_entry(log_id);
CREATE INDEX IF NOT EXISTS idx_file_instance_rom_id ON file_instance(rom_id);
CREATE INDEX IF NOT EXISTS idx_romset_member_version_id ON romset_member(version_id);
CREATE INDEX IF NOT EXISTS idx_playlist_item_playlist_id ON playlist_item(playlist_id);

-- Frequently Queried Columns
CREATE INDEX IF NOT EXISTS idx_rom_file_sha1 ON rom_file(sha1);
CREATE INDEX IF NOT EXISTS idx_dat_entry_rom_sha1 ON dat_entry(rom_sha1);
CREATE INDEX IF NOT EXISTS idx_dat_entry_clone_of ON dat_entry(clone_of);
