-- =============================================================================
-- ROM CURATOR DATABASE SEED SCRIPT
-- =============================================================================
-- This script seeds a fresh database with all existing data from RomCurator.db
-- Run this after creating the database schema to restore all imported data.
--
-- Usage: sqlite3 database/RomCurator.db < seed-scripts/run_all_seeds.sql
-- =============================================================================

-- Disable foreign key constraints during import
PRAGMA foreign_keys = OFF;

-- Begin transaction for atomicity
BEGIN TRANSACTION;

-- Import core reference data first
.read seed-scripts/01_metadata_source.sql
.read seed-scripts/02_import_log.sql
.read seed-scripts/03_platform.sql
.read seed-scripts/04_genre.sql
.read seed-scripts/05_company.sql

-- Import atomic game data
.read seed-scripts/06_atomic_game_unit.sql
.read seed-scripts/07_atomic_core_metadata.sql
.read seed-scripts/08_atomic_metadata_extension.sql

-- Import game release data
.read seed-scripts/09_game_release.sql
.read seed-scripts/10_release_developer.sql
.read seed-scripts/11_release_publisher.sql
.read seed-scripts/12_release_genre.sql

-- Import DAT data
.read seed-scripts/13_dat_entry.sql
.read seed-scripts/14_dat_entry_metadata.sql

-- Commit transaction
COMMIT;

-- Re-enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Analyze to update statistics
ANALYZE;

-- Show summary
SELECT 'Seed data import completed successfully!' as status;
SELECT 
    'atomic_game_unit' as table_name, 
    COUNT(*) as rows 
FROM atomic_game_unit
UNION ALL
SELECT 
    'game_release' as table_name, 
    COUNT(*) as rows 
FROM game_release
UNION ALL
SELECT 
    'dat_entry' as table_name, 
    COUNT(*) as rows 
FROM dat_entry
UNION ALL
SELECT 
    'company' as table_name, 
    COUNT(*) as rows 
FROM company
UNION ALL
SELECT 
    'platform' as table_name, 
    COUNT(*) as rows 
FROM platform
UNION ALL
SELECT 
    'genre' as table_name, 
    COUNT(*) as rows 
FROM genre;
