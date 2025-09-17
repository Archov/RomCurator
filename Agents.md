# ROM Curator - AI Agent Context Guide

## **Project Prime Directives**

* **North Star:** Build a tool that transforms chaos into control: take a sprawling mess of ROMs, ISOs, and random zips and create a single, trusted library folder structure that validates against DATs and applies sensible 1G1R rules. This becomes your permanent source of truth—an organized directory tree of validated files, searchable and versioned—so you never have to wonder "which folder has the good dump?" again. From this clean foundation, generate smart playlists using queries, genres, top-games lists, or any criteria that matters to you, then export exactly what each device needs in exactly the format it expects.  
* **Design Principle:** Every feature must reduce the total time from "I downloaded/changed something" to "all my devices are updated and organized." This means deterministic operations (so you can trust the results), smart diffing (so you only update what changed), and format-aware exports that understand what MiSTer vs EverDrive vs RetroArch actually need—even if that means duplicating or restructuring files. The architecture should be boring and bulletproof because the user's attention should be on playing games, not managing them. When there's a tradeoff between theoretical purity and "just works every time," we choose what works.

## Project Overview

**ROM Curator** is a desktop application for managing and curating ROM collections with intelligent metadata matching and 1G1R (1-Game-1-ROM) organization capabilities.

### Core Philosophy
- **Atomic Game Database**: Three-layer data model (`atomic_game_unit` → `game_release` → `rom_file`)
- **Metadata Integration**: Import from multiple sources (MobyGames, No-Intro, TOSEC, GoodTools)
- **Intelligent Matching**: Fuzzy string matching with confidence scoring
- **1G1R Curation**: Organize collections to have one "best" version per game
- **Platform Linking**: Handle different naming conventions (NES ↔ Nintendo Entertainment System)

## Tech Stack

- **Language**: Python 3.x
- **GUI Framework**: PyQt5 with qdarkstyle
- **Database**: SQLite3
- **Data Sources**: JSON (MobyGames), XML (No-Intro, TOSEC)
- **Matching**: Fuzzy string matching with confidence scoring

## Project Structure

```
RomCurator/
├── rom_curator_main.py          # Main application entry point
├── enhanced_importer_gui.py     # Data import interface  
├── curation_gui.py              # Manual curation interface
├── platform_linking_gui.py     # Platform relationship management (v2)
├── data_importer_gui.py         # Legacy importer (deprecated)
├── log_viewer.py                # Log viewing utility with session logs
├── start_rom_curator.py         # Application launcher
├── config.json                  # Application configuration
├── requirements.txt             # Python dependencies
├── Rom Curator Database.sql    # Database schema v1.8
├── Rom Curator Database Documentation.md  # Full schema documentation
├── README.md                    # User guide & quick start
├── Agents.md                    # AI agent context guide
├── refactoring_summary.md       # Code improvements documentation
├── .gitignore                   # Git ignore rules
├── fast_reseed_database.ps1    # Quick database reset script
├── reseed_database.ps1         # Database seeding script
├── dat_validation_queries.sql  # DAT validation SQL queries
├── seed-scripts/                # Database seeding scripts
│   ├── 01_metadata_source.sql
│   ├── 02_import_log.sql
│   ├── 03_platform.sql
│   ├── 04_genre.sql
│   ├── 05_company.sql
│   ├── 06_atomic_game_unit.sql
│   ├── 07_atomic_core_metadata.sql
│   ├── 08_atomic_metadata_extension.sql
│   ├── 09_game_release.sql
│   ├── 10_release_developer.sql
│   ├── 11_release_publisher.sql
│   ├── 12_release_genre.sql
│   ├── 13_dat_entry.sql
│   ├── 14_dat_entry_metadata.sql
│   ├── extract_inserts.ps1     # Extract seed data from database
│   ├── run_all_seeds.sql       # Execute all seed scripts
│   ├── run_inserts_only.sql    # Execute insert scripts only
│   ├── seed_database.ps1       # PowerShell seeding script
│   └── inserts/                # Extracted insert statements
├── scripts/seeders/             # Data import modules
│   ├── base_importer.py        # Shared import functionality
│   ├── mobygames.py            # MobyGames JSON importer
│   ├── no-intro.py             # No-Intro XML importer
│   ├── tosec.py                # TOSEC XML importer
│   ├── dat_parser.py           # DAT filename metadata parser
│   ├── matching_engine.py     # Intelligent matching system
│   ├── xml_utils.py            # XML processing utilities
│   └── archive/                # Archived/old versions
├── seed-data/                   # Sample seed data files
├── database/                    # Database storage directory
├── logs/                        # Application and import logs
├── external reference documentation/  # Additional documentation
└── .schema_cache/               # Cached schema files
```

## Database Schema (v1.8 - Platform Linking Edition)

### Core Tables (6)
- **`atomic_game_unit`**: Canonical game records
- **`game_release`**: Platform-specific releases
- **`rom_file`**: Individual ROM files
- **`platform`**: Gaming platforms
- **`company`**: Developers/publishers
- **`genre`**: Game genres

### Metadata Tables (4)
- **`atomic_core_metadata`**: Core game metadata
- **`atomic_metadata_extension`**: Extended metadata (EAV pattern)
- **`dat_entry`**: DAT file ROM entries with parsed metadata
- **`dat_entry_metadata`**: DAT-specific metadata (EAV pattern)

### Linking Tables (3)
- **`dat_atomic_link`**: Links between DAT entries and atomic games
- **`platform_links`**: Platform name relationships (NES ↔ Nintendo Entertainment System)
- **`file_instance`**: Links ROM files to their physical locations

### Company Management (3)
- **`company_alias_group`**: Groups of company aliases
- **`company_alias`**: Alternative company names
- **`region`**: Geographic regions

### Release Management (4)
- **`release_developer`**: Developer relationships
- **`release_publisher`**: Publisher relationships
- **`release_genre`**: Genre relationships
- **`release_region`**: Region relationships

### File Management (2)
- **`release_artifact`**: Artifacts (manuals, covers, etc.)
- **`library_root`**: Library root directories

### Import System (2)
- **`metadata_source`**: Data source definitions
- **`import_log`**: Import operation logs

### Curation System (3)
- **`selection_policy`**: 1G1R selection rules
- **`romset_version`**: ROMset versioning
- **`romset_member`**: ROMset membership

### Playlist System (2)
- **`playlist_item`**: Playlist entries
- **`playlist`**: User playlists

### Export System (3)
- **`target_device`**: Export target devices (defined, not implemented)
- **`export_profile`**: Export configurations (defined, not implemented)
- **`export_run`**: Export operation logs (defined, not implemented)

**Total: 32 tables** (29 actively used, 3 export tables defined but not yet implemented)

## Current Implementation Status

### ✅ Fully Implemented

#### 1. Data Import System
- **Expandable architecture**: Base importer class with format-specific implementations
- **MobyGames**: JSON import with game metadata, companies, genres
- **No-Intro**: XML DAT files with intelligent metadata parsing
- **TOSEC**: XML DAT files with comprehensive ROM data
- **Universal DAT Parser**: Extracts base title, region, version, dump status from filenames
- **Import Session Management**: Detailed logging, progress tracking, error recovery
- **Schema Validation**: XML/XSD validation with caching
- **Idempotent Operations**: File hash tracking prevents duplicate imports

#### 2. Intelligent Matching System  
- **Platform Linking v2**: Simplified atomic vs alias platform management
- **Platform Linking GUI**: Modern interface with drag-and-drop, filtering, search
- **Fuzzy String Matching**: Automatic game matching across naming conventions
- **Confidence Scoring**: Match quality ratings for review
- **Matching Engine**: Automatic and manual DAT-to-atomic game linking
- **Cross-Platform Search**: Searches DAT entries across linked platforms automatically

#### 3. GUI Infrastructure
- **Unified Main Application**: Single entry point with menu-driven access
- **Enhanced Import GUI**: Real-time progress, console output, error handling
- **Curation Interface**: Review and confirm matches manually
- **Log Viewer**: Session-specific logs with filtering and search
- **Dark Theme Support**: Consistent qdarkstyle theming
- **Configuration Management**: Centralized config.json for all settings

### 🚧 Partially Implemented

#### 4. Curation System
- **Manual Review**: GUI for reviewing matches (functional)
- **1G1R Logic**: Selection policy and romset versioning (database schema present, UI pending)
- **Clone Validation**: DAT clone relationship handling

## Configuration

### config.json
All application settings are centralized in this file:
```json
{
    "database_path": "./database/RomCurator.db",
    "importer_scripts_directory": "./scripts/seeders/",
    "log_directory": "./logs/",
    "log_level": "INFO",
    "auto_create_directories": true,
    "progress_update_interval": 100,
    "gui_settings": {
        "window_width": 1200,
        "window_height": 800,
        "theme": "dark"
    }
}
```

**Key Settings**:
- `database_path`: Location of the SQLite database
- `log_level`: DEBUG, INFO, WARNING, ERROR
- `auto_create_directories`: Automatically create missing directories
- `progress_update_interval`: How often to update progress bars

## Key Classes and Modules

### Core Application
- **`RomCuratorMainWindow`**: Main application window with menu system
- **`ConfigManager`**: Centralized configuration management  
- **`LoggingManager`**: Application logging with session support

### Import System
- **`BaseImporter`**: Abstract base class for all importers
- **`DatabaseHandler`**: Shared database operations (in base_importer.py)
- **`MobyGamesImporter`**: MobyGames JSON processing
- **`NoIntroImporter`**: No-Intro XML processing
- **`TosecImporter`**: TOSEC XML processing
- **`DATNameParser`**: Universal DAT filename metadata extraction
- **`XMLValidator`**: Schema validation utilities (xml_utils.py)

### Matching System
- **`GameMatcher`**: Core matching engine with fuzzy string matching
- **`MatchCandidate`**: Data class for match results
- **`PlatformLinkingDialog`**: v2 GUI for atomic/alias platform management
- **`PlatformAliasDialog`**: Sub-dialog for selecting platform aliases

### GUI Components
- **`ImporterApp`**: Enhanced data import interface with real-time progress
- **`CurationMainWindow`**: Manual curation interface
- **`LogViewerWindow`**: Log file viewer with session filtering
- **`DraggableTitleBar`**: Custom frameless window support for dark theme

## Data Flow

1. **Import**: Raw data → Importers → Database tables
2. **Parse**: DAT filenames → Metadata extraction → `dat_entry_metadata`
3. **Match**: Atomic games ↔ DAT entries via fuzzy matching
4. **Link**: Platform names → Platform relationships
5. **Curate**: Manual review → Confirmed matches
6. **Export**: Curated data → 1G1R collections

## Common Patterns

### Code Architecture (Refactored)
- **DRY Principle**: ~47% code reduction through shared base classes
- **BaseImporter**: All importers inherit common functionality
- **Shared utilities**: xml_utils.py, dat_parser.py for common operations
- **Consistent interfaces**: All importers follow same pattern

### Database Operations
- Use `INSERT OR IGNORE` for lookup tables
- Use `INSERT OR REPLACE` for data updates
- Use transactions for bulk operations
- Use `lastrowid` for getting inserted IDs
- Always check for existing imports via file hash

### Error Handling
- Log all operations with appropriate levels
- Use try/catch with rollback for database operations
- Provide user feedback via progress bars and status messages
- Validate data before processing

### GUI Patterns
- Inherit parent stylesheet for consistent theming
- Use frameless dialogs with custom title bars for dark theme
- Implement drag functionality for custom title bars
- Use QSplitter for resizable layouts

## Implementation Details

### Platform Linking Architecture (v2)

The platform linking system (v1.8) solves a critical matching problem:
- **Problem**: Atomic games use simplified platform names ("NES"), while DAT files use full names ("Nintendo Entertainment System")
- **Solution**: `platform_links` table creates atomic → alias relationships
- **Implementation**: 
  - `GameMatcher.get_linked_platform_ids()` automatically includes linked platforms in searches
  - Atomic platforms serve as canonical names for a group of aliases
  - Bidirectional search capabilities across all linked platforms
- **UI**: `PlatformLinkingDialog` v2 features:
  - Visual indicators: ⚛️ Atomic, 👓 Alias, ⚪ Unlinked
  - Make any platform in a group atomic
  - Add/remove aliases dynamically
  - Filter and search capabilities
  - Frameless dark theme support

### Import Session Management

Each import creates:
- **Master log entry**: In `import_log` table with file hash for idempotency
- **Session log file**: `logs/import_SourceName_YYYYMMDD_HHMMSS.log`
- **Progress tracking**: Real-time updates in GUI with console output

## Database Views

### Import & Data Quality Views
- **`v_imported_games_summary`**: Overview of all imported games with metadata
- **`v_import_statistics`**: Import stats by source
- **`v_data_completeness_issues`**: Games missing metadata
- **`v_games_with_platforms`**: Games with platform and metadata details
- **`v_potential_duplicates`**: Possible duplicate game entries

### DAT Validation Views  
- **`v_dat_import_summary`**: DAT import statistics with parsed metadata
- **`v_dat_rom_matching`**: SHA1 matching between DATs and ROM files
- **`v_dat_clone_validation`**: Clone relationship validation
- **`v_dat_orphaned_clones`**: Clones without parent entries
- **`v_dat_clone_summary`**: Clone statistics by platform
- **`v_dat_unlinked_entries`**: DAT entries not linked to releases
- **`v_dat_platform_analysis`**: Platform detection accuracy
- **`v_dat_import_health`**: Overall DAT import health metrics

### DAT Metadata Analysis Views
- **`v_dat_metadata_distribution`**: Distribution of parsed metadata
- **`v_dat_format_specific_metadata`**: Format-specific metadata usage
- **`v_dat_atomic_linking_candidates`**: Suggested DAT to atomic game links

## Development Guidelines

### File Naming
- No version numbers in filenames (use git history)
- Descriptive names: `platform_linking_gui.py`
- Test files: `test_*.py` (clean up after development)

### Code Organization
- One class per file for major components
- Shared utilities in `base_importer.py` and `xml_utils.py`
- Database operations in dedicated methods
- GUI logic separated from business logic

### Database Schema
- All tables defined in main schema file
- No patch scripts or version-specific schemas
- Document all changes in schema documentation

## Common Tasks

### Adding New Data Sources
1. Create importer class inheriting from `BaseImporter`
2. Implement `import_data()` method
3. Add to main application menu
4. Update documentation

### Adding New Metadata Fields
1. Add column to appropriate table
2. Update importer to populate field
3. Update matching engine if needed
4. Update GUI to display field

### Modifying Matching Logic
1. Update `GameMatcher` class methods
2. Adjust confidence thresholds
3. Test with existing data
4. Update curation interface if needed

## ❌ Not Yet Implemented

### Export System
- **Target device profiles**: MiSTer, EverDrive, RetroArch configurations
- **Path template system**: Format-aware export paths
- **Export run tracking**: History and rollback capabilities
- **Smart diffing**: Only export changed files
- **Format conversion**: Device-specific requirements

### Library Management  
- **File scanning**: Discover ROMs in library_root directories
- **File verification**: SHA1 validation against DAT entries
- **ROMset versioning UI**: Interface for creating/managing versions
- **Playlist generation**: Smart playlists from queries and genres
- **Duplicate detection**: Find and manage duplicate ROMs

### Advanced Curation
- **1G1R UI**: Complete interface for selection policies
- **Batch operations**: Apply curation rules to large sets
- **Auto-matching improvements**: Machine learning suggestions
- **Regional preferences**: Complex region priority rules

## Future Enhancements

### Near-term Priorities
- Complete 1G1R UI implementation
- Basic export system for common devices
- Library scanning and verification
- Playlist generation from curation results

### Long-term Vision
- Additional data sources (IGDB, Redump, MAME)
- Advanced ML-based matching algorithms
- Plugin architecture for custom importers
- Web interface for remote management
- Cloud sync and backup capabilities
- Multi-user support with permissions

---

## Quick Start for AI Agents

1. **Understand the data model**: Atomic games → Releases → ROMs
2. **Know the import flow**: Raw data → Parsers → Database → Matching
3. **Recognize the GUI structure**: Main app → Dialogs → Components
4. **Follow the patterns**: Database operations, error handling, theming
5. **Respect the architecture**: No versioned files, proper separation of concerns
6. **Use base classes**: Inherit from BaseImporter for new data sources
7. **Maintain consistency**: Follow established UI patterns and dark theme

## Current Project State Summary

**Completed Core Systems**:
- ✅ Robust data import pipeline with multiple sources
- ✅ Intelligent DAT metadata parsing
- ✅ Platform linking for cross-naming compatibility  
- ✅ Modern GUI with real-time feedback
- ✅ Comprehensive logging and error handling
- ✅ Refactored codebase following DRY principles

**Active Development**:
- 🚧 1G1R curation UI
- 🚧 Clone relationship validation
- 🚧 Library scanning

**Planned Next**:
- 📅 Export system implementation
- 📅 Playlist generation
- 📅 File verification tools

The foundation is solid and production-ready for import, matching, and basic curation. The architecture supports the planned export and library management features without requiring major refactoring.
