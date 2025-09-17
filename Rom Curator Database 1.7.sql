-- =============================================================================
-- ATOMIC GAME DATABASE SCHEMA v1.7 (Enhanced DAT Metadata)
--
-- Author:      Project Contributor
-- Created:     2025-09-16
-- Description: This version enhances the `dat_entry` table to include parsed
--              universal metadata concepts (base_title, region, version, etc.)
--              found across all major naming conventions (No-Intro, TOSEC, 
--              GoodTools), while adding `dat_entry_metadata` table for 
--              format-specific metadata using EAV pattern.
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
    importer_script TEXT,
    schema_file_path TEXT
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

-- Enhanced dat_entry with universal metadata concepts parsed from DAT naming conventions
CREATE TABLE IF NOT EXISTS dat_entry (
  dat_entry_id INTEGER PRIMARY KEY,
  log_id INTEGER NOT NULL REFERENCES import_log(log_id),
  platform_id INTEGER NOT NULL REFERENCES platform(platform_id), -- Stored for context
  release_title TEXT NOT NULL, -- Original full title from DAT
  rom_sha1 TEXT NOT NULL,
  external_id TEXT, -- The ID from the DAT file that clone_of references
  is_clone BOOLEAN NOT NULL DEFAULT 0,
  clone_of TEXT,
  -- Universal metadata concepts present across all major naming conventions
  base_title TEXT, -- Parsed clean title for atomic matching (e.g., "Super Mario Bros.")
  region_normalized TEXT, -- Standardized region code (USA/EUR/JPN/World/etc.)
  version_info TEXT, -- Version information (v1.02, Rev 1, REVXX, etc.)
  development_status TEXT, -- Development status (demo, beta, proto, alpha, sample)
  dump_status TEXT, -- Dump quality (verified, good, bad, alternate, overdump, underdump)
  language_codes TEXT -- Standardized language codes (en, ja, fr, en-de, M3, etc.)
);

-- Format-specific metadata storage using Entity-Attribute-Value pattern
CREATE TABLE IF NOT EXISTS dat_entry_metadata (
    dat_entry_id INTEGER NOT NULL REFERENCES dat_entry(dat_entry_id) ON DELETE CASCADE,
    metadata_key TEXT NOT NULL,
    metadata_value TEXT NOT NULL,
    PRIMARY KEY (dat_entry_id, metadata_key)
);

-- Links between atomic games and DAT entries for metadata/DAT matching system
CREATE TABLE IF NOT EXISTS dat_atomic_link (
    link_id INTEGER PRIMARY KEY,
    atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id) ON DELETE CASCADE,
    dat_entry_id INTEGER NOT NULL REFERENCES dat_entry(dat_entry_id) ON DELETE CASCADE,
    match_type TEXT NOT NULL CHECK (match_type IN ('manual', 'automatic', 'fuzzy')),
    confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_date TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (atomic_id, dat_entry_id)
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
CREATE INDEX IF NOT EXISTS idx_dat_entry_metadata_entry_id ON dat_entry_metadata(dat_entry_id);
CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_atomic ON dat_atomic_link(atomic_id);
CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_dat ON dat_atomic_link(dat_entry_id);
CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_type ON dat_atomic_link(match_type);
CREATE INDEX IF NOT EXISTS idx_file_instance_rom_id ON file_instance(rom_id);
CREATE INDEX IF NOT EXISTS idx_romset_member_version_id ON romset_member(version_id);
CREATE INDEX IF NOT EXISTS idx_playlist_item_playlist_id ON playlist_item(playlist_id);

-- Frequently Queried Columns
CREATE INDEX IF NOT EXISTS idx_rom_file_sha1 ON rom_file(sha1);
CREATE INDEX IF NOT EXISTS idx_dat_entry_rom_sha1 ON dat_entry(rom_sha1);
CREATE INDEX IF NOT EXISTS idx_dat_entry_clone_of ON dat_entry(clone_of);
CREATE INDEX IF NOT EXISTS idx_dat_entry_external_id ON dat_entry(external_id);

-- New indexes for parsed metadata columns
CREATE INDEX IF NOT EXISTS idx_dat_entry_base_title ON dat_entry(base_title);
CREATE INDEX IF NOT EXISTS idx_dat_entry_region_normalized ON dat_entry(region_normalized);
CREATE INDEX IF NOT EXISTS idx_dat_entry_dump_status ON dat_entry(dump_status);
CREATE INDEX IF NOT EXISTS idx_dat_entry_metadata_key ON dat_entry_metadata(metadata_key);


-- =============================================================================
-- SECTION 6: Views
-- =============================================================================
-- View to show all imported games with their basic metadata and import information
CREATE VIEW v_imported_games_summary AS
SELECT 
    agu.atomic_id,
    agu.canonical_title,
    acm.release_date,
    acm.description,
    il.file_name as imported_from,
    il.import_timestamp,
    ms.name as source_name,
    COUNT(DISTINCT gr.platform_id) as platform_count,
    COUNT(DISTINCT gr.release_id) as release_count
FROM atomic_game_unit agu
LEFT JOIN atomic_core_metadata acm ON agu.atomic_id = acm.atomic_id
LEFT JOIN import_log il ON acm.log_id = il.log_id
LEFT JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN game_release gr ON agu.atomic_id = gr.atomic_id
GROUP BY agu.atomic_id, agu.canonical_title, acm.release_date, acm.description, il.file_name, il.import_timestamp, ms.name;

-- View to show import statistics by source
CREATE VIEW v_import_statistics AS
SELECT 
    ms.name as source_name,
    il.status,
    COUNT(il.log_id) as import_count,
    SUM(il.records_processed) as total_records_processed,
    MAX(il.import_timestamp) as last_import,
    COUNT(DISTINCT il.file_name) as unique_files_processed
FROM import_log il
JOIN metadata_source ms ON il.source_id = ms.source_id
GROUP BY ms.name, il.status;

-- View to identify games with missing or incomplete metadata
CREATE VIEW v_data_completeness_issues AS
SELECT 
    agu.atomic_id,
    agu.canonical_title,
    CASE WHEN acm.atomic_id IS NULL THEN 1 ELSE 0 END as missing_core_metadata,
    CASE WHEN acm.release_date IS NULL OR acm.release_date = '' THEN 1 ELSE 0 END as missing_release_date,
    CASE WHEN gr.release_id IS NULL THEN 1 ELSE 0 END as no_releases,
    COUNT(DISTINCT gr.platform_id) as platform_count,
    COUNT(DISTINCT rd.company_id) as developer_count,
    COUNT(DISTINCT rp.company_id) as publisher_count,
    COUNT(DISTINCT rg.genre_id) as genre_count
FROM atomic_game_unit agu
LEFT JOIN atomic_core_metadata acm ON agu.atomic_id = acm.atomic_id
LEFT JOIN game_release gr ON agu.atomic_id = gr.atomic_id
LEFT JOIN release_developer rd ON gr.release_id = rd.release_id
LEFT JOIN release_publisher rp ON gr.release_id = rp.release_id
LEFT JOIN release_genre rg ON gr.release_id = rg.release_id
GROUP BY agu.atomic_id, agu.canonical_title, acm.atomic_id, acm.release_date;

-- View to show games with their platforms and key metadata
CREATE VIEW v_games_with_platforms AS
SELECT 
    agu.atomic_id,
    agu.canonical_title,
    p.name as platform_name,
    gr.release_title,
    acm.release_date,
    GROUP_CONCAT(DISTINCT c_dev.name) as developers,
    GROUP_CONCAT(DISTINCT c_pub.name) as publishers,
    GROUP_CONCAT(DISTINCT g.name) as genres,
    ame_score.value as moby_score,
    ame_url.value as moby_url
FROM atomic_game_unit agu
JOIN game_release gr ON agu.atomic_id = gr.atomic_id
JOIN platform p ON gr.platform_id = p.platform_id
LEFT JOIN atomic_core_metadata acm ON agu.atomic_id = acm.atomic_id
LEFT JOIN release_developer rd ON gr.release_id = rd.release_id
LEFT JOIN company c_dev ON rd.company_id = c_dev.company_id
LEFT JOIN release_publisher rp ON gr.release_id = rp.release_id
LEFT JOIN company c_pub ON rp.company_id = c_pub.company_id
LEFT JOIN release_genre rg ON gr.release_id = rg.release_id
LEFT JOIN genre g ON rg.genre_id = g.genre_id
LEFT JOIN atomic_metadata_extension ame_score ON agu.atomic_id = ame_score.atomic_id AND ame_score.key = 'moby_score'
LEFT JOIN atomic_metadata_extension ame_url ON agu.atomic_id = ame_url.atomic_id AND ame_url.key = 'moby_url'
GROUP BY agu.atomic_id, p.platform_id;

-- View to identify potential duplicate titles that might need curation
CREATE VIEW v_potential_duplicates AS
SELECT 
    LOWER(TRIM(canonical_title)) as normalized_title,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(atomic_id) as atomic_ids,
    GROUP_CONCAT(canonical_title, ' | ') as titles
FROM atomic_game_unit
GROUP BY LOWER(TRIM(canonical_title))
HAVING COUNT(*) > 1;

-- =============================================================================
-- DAT VALIDATION VIEWS (Updated for v1.7)
-- =============================================================================

-- View to show DAT import summary with detailed statistics including parsed metadata
CREATE VIEW v_dat_import_summary AS
SELECT 
    ms.name as source_name,
    il.file_name,
    il.import_timestamp,
    il.status,
    il.records_processed,
    COUNT(de.dat_entry_id) as dat_entries_created,
    COUNT(CASE WHEN de.is_clone = 0 THEN 1 END) as parent_roms,
    COUNT(CASE WHEN de.is_clone = 1 THEN 1 END) as clone_roms,
    COUNT(DISTINCT de.platform_id) as platforms_detected,
    COUNT(CASE WHEN de.base_title IS NOT NULL THEN 1 END) as entries_with_parsed_title,
    COUNT(CASE WHEN de.region_normalized IS NOT NULL THEN 1 END) as entries_with_parsed_region,
    COUNT(CASE WHEN de.dump_status IS NOT NULL THEN 1 END) as entries_with_dump_status,
    il.notes
FROM import_log il
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN dat_entry de ON il.log_id = de.log_id
GROUP BY il.log_id, ms.name, il.file_name, il.import_timestamp, il.status, il.records_processed, il.notes;

-- View to validate SHA1 matching between DAT entries and ROM files (updated with new columns)
CREATE VIEW v_dat_rom_matching AS
SELECT 
    de.dat_entry_id,
    de.release_title,
    de.base_title,
    de.region_normalized,
    de.version_info,
    de.dump_status,
    p.name as platform_name,
    ms.name as source_name,
    de.rom_sha1,
    CASE 
        WHEN rf.sha1 IS NOT NULL THEN 'MATCHED'
        ELSE 'UNMATCHED'
    END as match_status,
    rf.rom_id,
    rf.filename as rom_filename,
    rf.size_bytes,
    de.is_clone,
    de.clone_of
FROM dat_entry de
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
JOIN platform p ON de.platform_id = p.platform_id
LEFT JOIN rom_file rf ON LOWER(de.rom_sha1) = LOWER(rf.sha1);

-- View to identify clone relationship validation issues
-- Updated to use external_id for proper clone matching
CREATE VIEW v_dat_clone_validation AS
SELECT 
    parent.external_id as parent_external_id,
    parent.release_title as parent_title,
    parent.base_title as parent_base_title,
    parent.rom_sha1 as parent_sha1,
    COUNT(clone.dat_entry_id) as clone_count,
    GROUP_CONCAT(clone.release_title, ' | ') as clone_titles,
    GROUP_CONCAT(DISTINCT clone.base_title, ' | ') as clone_base_titles,
    p.name as platform_name,
    ms.name as source_name,
    il.file_name
FROM dat_entry parent
JOIN platform p ON parent.platform_id = p.platform_id
JOIN import_log il ON parent.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN dat_entry clone ON parent.external_id = clone.clone_of 
    AND parent.platform_id = clone.platform_id
    AND parent.log_id = clone.log_id
WHERE parent.is_clone = 0
    AND parent.external_id IS NOT NULL
GROUP BY parent.dat_entry_id, parent.external_id, parent.release_title, parent.base_title, parent.rom_sha1, p.name, ms.name, il.file_name
HAVING clone_count > 0
ORDER BY clone_count DESC;

-- View to show orphaned clone entries (clones without parents)
-- Updated to use external_id for proper clone matching
CREATE VIEW v_dat_orphaned_clones AS
SELECT 
    clone.dat_entry_id,
    clone.release_title as clone_title,
    clone.base_title as clone_base_title,
    clone.clone_of as supposed_parent_id,
    p.name as platform_name,
    ms.name as source_name,
    il.file_name,
    clone.rom_sha1
FROM dat_entry clone
JOIN platform p ON clone.platform_id = p.platform_id
JOIN import_log il ON clone.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN dat_entry parent ON clone.clone_of = parent.external_id 
    AND clone.platform_id = parent.platform_id
    AND clone.log_id = parent.log_id
    AND parent.is_clone = 0
WHERE clone.is_clone = 1 
    AND clone.clone_of IS NOT NULL 
    AND clone.clone_of != ''
    AND parent.dat_entry_id IS NULL;

-- View to show basic clone statistics without parent resolution
CREATE VIEW v_dat_clone_summary AS
SELECT 
    ms.name as source_name,
    il.file_name,
    p.name as platform_name,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN is_clone = 0 THEN 1 END) as parent_entries,
    COUNT(CASE WHEN is_clone = 1 THEN 1 END) as clone_entries,
    COUNT(DISTINCT CASE WHEN is_clone = 1 THEN clone_of END) as unique_parent_ids,
    COUNT(CASE WHEN is_clone = 1 AND parent.external_id IS NOT NULL THEN 1 END) as clones_with_matching_parent,
    ROUND((COUNT(CASE WHEN is_clone = 1 THEN 1 END) * 100.0) / COUNT(*), 2) as clone_percentage
FROM dat_entry de
JOIN platform p ON de.platform_id = p.platform_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN dat_entry parent ON de.clone_of = parent.external_id 
    AND de.platform_id = parent.platform_id
    AND de.log_id = parent.log_id
    AND parent.is_clone = 0
GROUP BY ms.name, il.file_name, p.name
ORDER BY ms.name, il.file_name;

-- View to show DAT entries that haven't been linked to game releases
CREATE VIEW v_dat_unlinked_entries AS
SELECT 
    de.dat_entry_id,
    de.release_title,
    de.base_title,
    de.region_normalized,
    de.dump_status,
    p.name as platform_name,
    ms.name as source_name,
    il.file_name,
    de.rom_sha1,
    de.is_clone,
    CASE 
        WHEN rf.sha1 IS NOT NULL THEN 'ROM_EXISTS'
        ELSE 'ROM_MISSING'
    END as rom_status
FROM dat_entry de
JOIN platform p ON de.platform_id = p.platform_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN rom_file rf ON LOWER(de.rom_sha1) = LOWER(rf.sha1)
LEFT JOIN release_artifact ra ON rf.rom_id = ra.rom_id
LEFT JOIN game_release gr ON ra.release_id = gr.release_id 
    AND de.platform_id = gr.platform_id
WHERE gr.release_id IS NULL;

-- View to analyze platform detection accuracy from DAT imports
CREATE VIEW v_dat_platform_analysis AS
SELECT 
    ms.name as source_name,
    il.file_name,
    p.name as detected_platform,
    COUNT(de.dat_entry_id) as entry_count,
    COUNT(CASE WHEN de.is_clone = 0 THEN 1 END) as parent_count,
    COUNT(CASE WHEN de.is_clone = 1 THEN 1 END) as clone_count,
    COUNT(DISTINCT de.release_title) as unique_titles,
    COUNT(DISTINCT de.base_title) as unique_base_titles,
    COUNT(CASE WHEN de.is_clone = 1 AND parent.external_id IS NOT NULL THEN 1 END) as clones_with_matching_parent
FROM dat_entry de
JOIN platform p ON de.platform_id = p.platform_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN dat_entry parent ON de.clone_of = parent.external_id 
    AND de.platform_id = parent.platform_id
    AND de.log_id = parent.log_id
    AND parent.is_clone = 0
GROUP BY ms.name, il.file_name, p.name
ORDER BY ms.name, il.file_name, entry_count DESC;

-- View to show overall DAT import health metrics (updated for v1.7)
CREATE VIEW v_dat_import_health AS
SELECT 
    ms.name as source_name,
    COUNT(DISTINCT il.log_id) as total_imports,
    COUNT(CASE WHEN il.status = 'completed' THEN 1 END) as successful_imports,
    COUNT(CASE WHEN il.status = 'failed' THEN 1 END) as failed_imports,
    SUM(il.records_processed) as total_records_processed,
    COUNT(DISTINCT de.dat_entry_id) as total_dat_entries,
    COUNT(DISTINCT de.platform_id) as platforms_covered,
    ROUND(
        (COUNT(CASE WHEN rf.sha1 IS NOT NULL THEN 1 END) * 100.0) / 
        NULLIF(COUNT(de.dat_entry_id), 0), 2
    ) as rom_match_percentage,
    ROUND(
        (COUNT(CASE WHEN de.base_title IS NOT NULL THEN 1 END) * 100.0) / 
        NULLIF(COUNT(de.dat_entry_id), 0), 2
    ) as parsing_success_percentage,
    MAX(il.import_timestamp) as last_successful_import
FROM metadata_source ms
LEFT JOIN import_log il ON ms.source_id = il.source_id
LEFT JOIN dat_entry de ON il.log_id = de.log_id
LEFT JOIN rom_file rf ON LOWER(de.rom_sha1) = LOWER(rf.sha1)
WHERE ms.importer_script LIKE '%dat%' OR ms.importer_script LIKE '%no-intro%' OR ms.importer_script LIKE '%tosec%' OR ms.name LIKE '%DAT%' OR ms.name LIKE '%No-Intro%' OR ms.name LIKE '%TOSEC%'
GROUP BY ms.source_id, ms.name;

-- =============================================================================
-- DAT METADATA ANALYSIS VIEWS (New in v1.7)
-- =============================================================================

-- View to show parsed metadata distribution across DAT entries
CREATE VIEW v_dat_metadata_distribution AS
SELECT 
    ms.name as source_name,
    il.file_name,
    p.name as platform_name,
    de.region_normalized,
    de.development_status,
    de.dump_status,
    de.language_codes,
    COUNT(*) as entry_count,
    COUNT(DISTINCT de.base_title) as unique_base_titles
FROM dat_entry de
JOIN platform p ON de.platform_id = p.platform_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
WHERE de.base_title IS NOT NULL
GROUP BY ms.name, il.file_name, p.name, de.region_normalized, de.development_status, de.dump_status, de.language_codes
ORDER BY ms.name, il.file_name, entry_count DESC;

-- View to show format-specific metadata usage from dat_entry_metadata
CREATE VIEW v_dat_format_specific_metadata AS
SELECT 
    ms.name as source_name,
    dem.metadata_key,
    dem.metadata_value,
    COUNT(*) as usage_count,
    COUNT(DISTINCT de.base_title) as unique_games_affected
FROM dat_entry_metadata dem
JOIN dat_entry de ON dem.dat_entry_id = de.dat_entry_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
GROUP BY ms.name, dem.metadata_key, dem.metadata_value
ORDER BY ms.name, dem.metadata_key, usage_count DESC;

-- View to identify DAT entries that need atomic game linking based on base_title
CREATE VIEW v_dat_atomic_linking_candidates AS
SELECT 
    de.dat_entry_id,
    de.base_title,
    de.region_normalized,
    de.platform_id,
    p.name as platform_name,
    ms.name as source_name,
    de.dump_status,
    de.is_clone,
    -- Try to find potential atomic game matches
    agu.atomic_id as potential_atomic_match,
    agu.canonical_title,
    CASE 
        WHEN agu.atomic_id IS NOT NULL THEN 'POTENTIAL_MATCH'
        ELSE 'NO_MATCH'
    END as match_status
FROM dat_entry de
JOIN platform p ON de.platform_id = p.platform_id
JOIN import_log il ON de.log_id = il.log_id
JOIN metadata_source ms ON il.source_id = ms.source_id
LEFT JOIN atomic_game_unit agu ON LOWER(TRIM(de.base_title)) = LOWER(TRIM(agu.canonical_title))
WHERE de.base_title IS NOT NULL
    AND de.dump_status NOT IN ('bad', 'overdump', 'underdump')  -- Focus on good dumps
ORDER BY match_status, de.base_title;