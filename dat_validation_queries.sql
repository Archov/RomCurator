-- =============================================================================
-- DAT IMPORT VALIDATION QUERIES
--
-- Use these queries to validate that DAT files (No-Intro, TOSEC, etc.) are
-- importing correctly and linking data properly.
-- =============================================================================

-- 1. Check overall DAT import health
-- This gives you a high-level overview of all DAT imports
SELECT * FROM v_dat_import_health 
ORDER BY source_name;

-- 2. Review recent DAT imports with detailed statistics
-- Shows the last 10 DAT imports with entry counts and clone analysis
SELECT 
    source_name,
    file_name,
    import_timestamp,
    status,
    records_processed,
    dat_entries_created,
    parent_roms,
    clone_roms,
    platforms_detected,
    CASE 
        WHEN records_processed = dat_entries_created THEN 'MATCH'
        ELSE 'MISMATCH - CHECK NOTES'
    END as processing_consistency,
    notes
FROM v_dat_import_summary 
WHERE status IN ('completed', 'failed')
ORDER BY import_timestamp DESC 
LIMIT 10;

-- 3. Identify failed imports that need attention
SELECT 
    source_name,
    file_name,
    import_timestamp,
    records_processed,
    notes
FROM v_dat_import_summary 
WHERE status = 'failed'
ORDER BY import_timestamp DESC;

-- 4. Check SHA1 matching rates by platform
-- This tells you how many DAT entries have corresponding ROM files
SELECT 
    platform_name,
    source_name,
    COUNT(*) as total_dat_entries,
    COUNT(CASE WHEN match_status = 'MATCHED' THEN 1 END) as matched_entries,
    COUNT(CASE WHEN match_status = 'UNMATCHED' THEN 1 END) as unmatched_entries,
    ROUND(
        (COUNT(CASE WHEN match_status = 'MATCHED' THEN 1 END) * 100.0) / COUNT(*), 2
    ) as match_percentage
FROM v_dat_rom_matching
GROUP BY platform_name, source_name
ORDER BY platform_name, source_name;

-- 5. Find orphaned clones (clones without parent entries)
-- These indicate potential DAT file corruption or import issues
SELECT 
    source_name,
    platform_name,
    clone_title,
    supposed_parent_id,
    rom_sha1
FROM v_dat_orphaned_clones
ORDER BY source_name, platform_name, clone_title;

-- 6. Review clone relationships
-- Shows parent games and their clones for validation
SELECT 
    source_name,
    platform_name,
    parent_external_id,
    parent_title,
    clone_count,
    clone_titles
FROM v_dat_clone_validation
WHERE clone_count > 0
ORDER BY source_name, platform_name, clone_count DESC
LIMIT 20;

-- 7. Find DAT entries that aren't linked to game releases
-- These are valid DAT entries but haven't been connected to the main game database
SELECT 
    platform_name,
    source_name,
    COUNT(*) as unlinked_count,
    COUNT(CASE WHEN rom_status = 'ROM_EXISTS' THEN 1 END) as have_rom_files,
    COUNT(CASE WHEN rom_status = 'ROM_MISSING' THEN 1 END) as missing_rom_files
FROM v_dat_unlinked_entries
GROUP BY platform_name, source_name
ORDER BY unlinked_count DESC;

-- 8. Platform detection accuracy analysis
-- Shows how well the importer is detecting platforms from DAT files
SELECT 
    source_name,
    detected_platform,
    entry_count,
    parent_count,
    clone_count,
    unique_titles,
    clones_with_matching_parent,
    ROUND((clone_count * 100.0) / NULLIF(entry_count, 0), 2) as clone_percentage
FROM v_dat_platform_analysis
ORDER BY source_name, entry_count DESC;

-- 9. Quick validation checklist
-- A simple pass/fail check for common issues
SELECT 
    'Total DAT Sources' as check_type,
    COUNT(DISTINCT source_name) as count,
    CASE WHEN COUNT(DISTINCT source_name) > 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM v_dat_import_health
WHERE total_dat_entries > 0

UNION ALL

SELECT 
    'Sources with Failed Imports' as check_type,
    COUNT(*) as count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END as status
FROM v_dat_import_health
WHERE failed_imports > 0

UNION ALL

SELECT 
    'Orphaned Clone Entries' as check_type,
    COUNT(*) as count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END as status
FROM v_dat_orphaned_clones

UNION ALL

SELECT 
    'Average ROM Match Rate' as check_type,
    ROUND(AVG(rom_match_percentage), 2) as count,
    CASE 
        WHEN AVG(rom_match_percentage) >= 80 THEN 'PASS'
        WHEN AVG(rom_match_percentage) >= 50 THEN 'WARN'
        ELSE 'FAIL'
    END as status
FROM v_dat_import_health
WHERE total_dat_entries > 0;

-- 10. Sample DAT entries for manual inspection
-- Shows a few entries from each source for spot-checking
SELECT 
    source_name,
    platform_name,
    release_title,
    rom_sha1,
    is_clone,
    clone_of,
    match_status
FROM v_dat_rom_matching
WHERE dat_entry_id IN (
    SELECT MIN(dat_entry_id)
    FROM v_dat_rom_matching
    GROUP BY source_name, platform_name
)
ORDER BY source_name, platform_name;
