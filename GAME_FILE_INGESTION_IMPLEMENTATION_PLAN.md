# ROM Curator: File Ingestion and Processing Implementation Plan

## 1. File Discovery and Inventory

### 1.1 Directory Scanning
- Leverage the existing `library_root` table to track configured library paths
- Implement recursive directory scanning to discover all game files within library roots
- Track file paths, sizes, and modification dates in the `file_instance` table

### 1.2 File Extension Management

#### Database Schema
```sql
-- File type categories (ROM, Archive, Disc Image, etc.)
CREATE TABLE IF NOT EXISTS file_type_category (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT 1
);

-- File extensions with rich metadata
CREATE TABLE IF NOT EXISTS file_extension (
    extension TEXT PRIMARY KEY,  -- e.g., 'nes', 'smc' (without dot)
    category_id INTEGER REFERENCES file_type_category(category_id),
    description TEXT,
    is_compressed BOOLEAN DEFAULT 0,
    is_disc_image BOOLEAN DEFAULT 0,
    is_archive BOOLEAN DEFAULT 0,
    is_bios BOOLEAN DEFAULT 0,
    is_save_file BOOLEAN DEFAULT 0,
    is_patch_file BOOLEAN DEFAULT 0,
    is_playlist BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Platform-specific extensions (many-to-many)
CREATE TABLE IF NOT EXISTS platform_extension (
    platform_id INTEGER REFERENCES platform(platform_id),
    extension TEXT REFERENCES file_extension(extension),
    is_primary BOOLEAN DEFAULT 0,
    PRIMARY KEY (platform_id, extension)
);

-- Tracks contents of archive files (ZIP, 7Z, RAR, etc.)
CREATE TABLE IF NOT EXISTS archive_contents (
    archive_rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    content_rom_id INTEGER NOT NULL REFERENCES rom_file(rom_id) ON DELETE CASCADE,
    path_in_archive TEXT NOT NULL,  -- Relative path within the archive
    file_size INTEGER NOT NULL,      -- Uncompressed size in bytes
    compression_ratio REAL,          -- Compression ratio (0-1, where lower is better)
    is_primary BOOLEAN DEFAULT 0,    -- Whether this is the primary ROM in the archive
    file_order INTEGER,              -- Order of files in the archive
    last_modified TEXT,              -- Last modified timestamp of the file in the archive
    PRIMARY KEY (archive_rom_id, content_rom_id)
);
```

#### Default Extensions
- **ROM Files**: `.nes`, `.smc`, `.sfc`, `.gba`, `.nds`, `.gb`, `.gbc`, `.n64`, `.z64`, `.v64`, `.a26`, `.a78`, `.lnx`
- **Compressed Archives**: `.zip`, `.7z`, `.rar`
- **Disc Images**: `.iso`, `.bin`, `.cue`, `.chd`, `.gdi`, `.cdi`
- **Save Files**: `.srm`, `.sav`, `.eep`, `.fla`, `.mcr`
- **Patches**: `.ips`, `.bps`, `.ups`, `.xdelta`
- **Playlists**: `.m3u`, `.m3u8`

#### Processing Rules
- **Inclusion/Exclusion**:
  - Process files with extensions marked as active in the database
  - Skip system files (`.DS_Store`, `thumbs.db`, `desktop.ini`)
  - Respect `.nomedia` and `.no-roms` marker files
  - Skip system directories (`__MACOSX`, `System Volume Information`)

#### User Interface
- **Extension Manager**:
  - List all known file extensions with filtering/sorting
  - Toggle extensions on/off
  - Add new custom extensions
  - Assign extensions to platforms
  - View file type statistics
- **Bulk Operations**:
  - Import/export extension lists
  - Enable/disable by category
  - Reset to defaults
- **Discovery Mode**:
  - Scan directories and suggest new extensions
  - Show statistics on file types found
  - One-click enable/disable of discovered extensions

## 2. File Processing Pipeline

### 2.1 File Type Detection
- **Primary Method**: File extension matching against configured lists
- **Fallback**: Magic number/header analysis for ambiguous files
- **Classification**:
  - **Single-file ROMs**: Direct ROM files with known extensions
  - **Compressed Archives**: Multi-file containers that need extraction
  - **Disc Images**: CD/DVD/Blu-ray images with game data
  - **Multi-file ROMs**: ROMs that span multiple files (e.g., `.bin` + `.cue`)

### 2.2 Hashing Strategy
- **Uncompressed Files**:
  - Calculate SHA-1 hash of the complete file (stored in `rom_file.sha1`)
  - Calculate additional hashes (MD5, CRC32) for compatibility
  - For large files (>100MB), use memory-efficient hashing with chunks
  - Store file size in bytes and last modified timestamp

- **Compressed Files**:
  - **Single ROM Archives**:
    1. Extract file to memory/temp
    2. Calculate hash of the extracted content
    3. Store in `rom_file` table with metadata
    4. Create `file_instance` record linked to the `rom_file`
  
  - **Multi-ROM Archives** (e.g., No-Intro packs, TOSEC sets):
    1. Extract all files in the archive to a temporary location
    2. Process each file individually:
       - Calculate hashes for each file
       - Create `rom_file` entries for each unique file
       - Store archive membership in `archive_contents` table
    3. Maintain archive structure in `file_instance` with:
       - Original archive path and metadata
       - Number of ROMs contained
       - Compression ratio
    4. Option to extract all ROMs to library during hashing (user-configurable)
  
  - **Multi-disc Sets** (e.g., PlayStation, Sega CD games):
    1. Identify related disc files (e.g., `Game (Disc 1).chd`, `Game (Disc 2).chd`)
    2. Group them as a single logical game
    3. Store relationship in `game_discs` table
    4. Allow launching the appropriate disc based on game requirements
  
  - **Batch Processing Options**:
    - Extract all ROMs to library (flattened structure)
    - Keep in archives but index all contents
    - User-defined rules for handling different archive types

### 2.3 Metadata Extraction
- **File Metadata**:
  - File name and extension
  - File size (compressed and uncompressed if applicable)
  - Last modified timestamp
  - File permissions and attributes

- **ROM-Specific Metadata**:
  - Header information (when available)
  - ROM size
  - Checksums (CRC32, MD5, SHA-1)
  - Internal ROM header information (title, region, version)

## 3. Database Integration

### 3.1 File Tracking
- **`file_instance` Table**:
  - Track physical file locations and attributes
  - Link to `library_root` for organization
  - Store relative paths for portability
  - Track first/last seen timestamps

### 3.2 ROM File Registry
- **`rom_file` Table**:
  - Store unique ROM files by hash
  - Track file size and hashes
  - Record first/last seen timestamps
  - Link to original source file

### 3.3 Archive Contents
- **Archive Handling**:
  - Store archive structure and contents
  - Track which files have been processed
  - Maintain relationships between archives and extracted ROMs

## 4. Performance and Optimization

### 4.1 Batch Processing
- Process files in configurable batch sizes
- Use database transactions for batch operations
- Implement progress tracking and reporting
## 4. Processing Pipeline

### 4.1 Initial Scan
1. Scan all directories in `library_root`
2. For each file:
   - Create/update `file_instance` record
   - If new or modified, calculate hashes and update `rom_file`
   - Link to `library_root` via `root_id`
   - Set `last_seen` timestamp

### 4.2 DAT Matching Phase
1. Load DAT files through `metadata_source` and `import_log`
2. For each ROM file:
   - Attempt exact hash match in `dat_entry`
   - If no match, try fuzzy matching using `base_title` and platform
   - Record matches in `dat_atomic_link` with appropriate confidence

### 4.3 Post-Processing
1. Identify unmatched files for review
2. Flag potential duplicates using `rom_file` hashes
3. Generate reports on collection status and matching statistics

## 5. Performance Considerations

### 5.1 Batch Processing
- Process files in batches to manage memory usage
- Use database transactions for bulk operations
- Implement progress reporting using the existing logging system

### 5.2 Caching
- Cache file hashes to avoid re-processing unchanged files
- Use `last_seen` timestamp for incremental updates
- Maintain in-memory index of known ROM hashes for quick lookups

### 5.3 Parallel Processing
- Process multiple files in parallel (with configurable concurrency)
- Implement work queues for balanced resource usage
- Respect system resources to avoid excessive memory/CPU usage

## 6. Error Handling and Recovery

### 6.1 Error Conditions
- Corrupt archives
- Permission issues
- Unsupported file formats
- Hash calculation failures
- Database constraint violations

### 6.2 Recovery Mechanisms
- Database transaction rollback on failure
- Detailed error logging to `import_log`
- Resume capabilities for interrupted scans
- Option to skip problem files and continue

## 7. Integration with Existing Components

### 7.1 Logging
- Use the existing `LoggingManager` for application logs
- Create detailed import logs in the `logs/` directory
- Include timestamps and operation details for debugging

### 7.2 Configuration
- Read settings from `config.json` via `ConfigManager`
- Support configuration of:
  - Library root directories
  - File type preferences
  - Hashing behavior
  - Performance settings

## 8. Testing Strategy

### 8.1 Unit Tests
- File format detection
- Hash calculation
- DAT parsing and normalization
- Database operations

### 8.2 Integration Tests
- End-to-end processing of sample collections
- DAT matching accuracy with known test sets
- Performance with large collections

### 8.3 Test Data
- Create test fixtures with known-good ROMs
- Include edge cases (corrupt files, unusual filenames, etc.)
- Test with various DAT file formats

## 9. Future Enhancements

### 9.1 Performance Optimizations
- Background processing for large collections
- Incremental updates for changed files only
- Optimized database indexes for common queries

### 9.2 Enhanced Matching
- Improved fuzzy matching algorithms
- Machine learning for better title normalization
- Community-sourced matching overrides

### 10.2 Additional Features
- Automatic ROM renaming
- Thumbnail generation
- Integration with emulator frontends

## 11. Implementation Phases

### Phase 1: Core Functionality
- Basic file scanning and hashing
- Simple DAT matching
- Basic database schema

### Phase 2: Advanced Features
- Compressed file support
- Advanced DAT parsing
- Performance optimizations

### Phase 3: Polish and Refinement
- Error handling
- User interface improvements
- Comprehensive testing

## 12. Dependencies

### Required Libraries
- `py7zr` for 7z archive support
- `rarfile` for RAR archive support
- `python-libarchive-c` for general archive support
- `crcmod` for CRC calculations
- `cryptography` for secure hashing

## 13. Security Considerations

### 13.1 File Handling
- Validate all file paths to prevent directory traversal
- Set appropriate file permissions
- Handle potentially malicious archives safely

### 13.2 Resource Usage
- Implement file size limits
- Set timeouts for archive operations
- Clean up temporary files properly

## 14. Documentation

### 14.1 User Documentation
- File format support
- DAT file requirements
- Troubleshooting guide

### 14.2 Developer Documentation
- Code organization
- Database schema
- Extension points

## 15. Maintenance Plan

### 15.1 Versioning
- Follow semantic versioning
- Maintain changelog

### 15.2 Updates
- Regular updates for new DAT files
- Support for new file formats as needed

## 16. Conclusion

This implementation plan provides a comprehensive approach to parsing and processing game collections for the ROM Curator application. By following this plan, we can build a robust system that handles the complexities of ROM management while providing a solid foundation for future enhancements.
