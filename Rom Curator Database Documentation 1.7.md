# **Atomic Game Database \- Architecture Documentation v1.7**

## **Project Prime Directives**

* **North Star:** Build a tool that transforms chaos into control: take a sprawling mess of ROMs, ISOs, and random zips and create a single, trusted **library folder structure** that validates against DATs and applies sensible 1G1R rules. This becomes your permanent source of truth—an organized directory tree of validated files, searchable and versioned—so you never have to wonder "which folder has the good dump?" again. From this clean foundation, generate smart playlists using queries, genres, top-games lists, or any criteria that matters to you, then export exactly what each device needs in exactly the format it expects.  
* **Design Principle:** Every feature must reduce the total time from "I downloaded/changed something" to "all my devices are updated and organized." This means deterministic operations (so you can trust the results), smart diffing (so you only update what changed), and format-aware exports that understand what MiSTer vs EverDrive vs RetroArch actually need—even if that means duplicating or restructuring files. The architecture should be boring and bulletproof because the user's attention should be on playing games, not managing them. When there's a tradeoff between theoretical purity and "just works every time," we choose what works.

## **1\. Introduction & Philosophy**

This document details the architecture of the Atomic Game Database, a schema designed to solve the complex problem of managing a personal game library by validating it against known-good sets (DAT files) and enriching it with external metadata.

The core philosophy is a hybrid approach that balances two needs:

1. **Operational Focus:** The schema must directly enable the core user stories: importing local files, creating versioned 1-Game-1-ROM (1G1R) sets, and exporting curated playlists to target devices.  
2. **Governance & Curation:** The schema must be robust enough to handle the chaotic reality of game data, including regional title differences (e.g., Final Fantasy III vs. VI), sloppy company naming ("Square Enix Ltd" vs "Square Enix, Inc."), and conflicting metadata from different sources.

It achieves this by separating the logical "concept" of a game from its physical releases and the files that represent them.

## **2\. Core Concepts**

Understanding these three concepts is key to using the database correctly.

* **`atomic_game_unit` (The Concept):** This is the highest level of abstraction. It represents the platonic ideal of a game, independent of platform or region. For example, there is only one `atomic_game_unit` for "Chrono Trigger". Playlists and high-level collections link to this entity.  
* **`game_release` (The Physical Product):** This represents a specific, physical or digital product that was sold. For example, "Chrono Trigger (SNES, USA)" and "Chrono Trigger (PlayStation, Japan)" are two different `game_release` records, but they both link to the same `atomic_game_unit`.  
* **`rom_file` (The Digital Representation):** This represents a single digital file, identified uniquely by its SHA1 hash. A `game_release` can be represented by one or more `rom_file`s via the `release_artifact` table (e.g., for multi-disc games).

## **3\. Schema Breakdown (v1.7)**

The schema is organized into logical sections.

### **Section 1: Core Governance & Metadata**

These tables define the "who, what, and where" of the game world and store the rich, descriptive metadata about them.

* **`company`, `company_alias_group`, `company_alias`**: A robust system for normalizing company names. All variations ("Square Soft", "Square Enix, Inc.") can be grouped and resolved to a single canonical `company` entry.  
* **`genre`, `platform`, `region`**: Simple, canonical lookup tables for core attributes.  
* **`atomic_game_unit`**: The central "concept" table, as described above.  
* **`atomic_core_metadata`**: A table with fixed columns for the most important, frequently queried data (description, release date). This ensures performance and data integrity for core attributes.  
* **`atomic_metadata_extension`**: A flexible key-value table for all other "long-tail" metadata (Moby Score, specific URLs, etc.), ensuring future extensibility. This completes the **Hybrid Metadata Model**.

### **Section 2: Release & Artifact Model**

This section models a specific, shippable product and precisely links it to its component parts and the digital files that represent them.

* **`game_release`**: The specific product release table. Stores the release-specific title, platform, edition, etc.  
* **`release_developer`, `release_publisher`, `release_genre`, `release_region`**: Junction tables that link a specific `game_release` to its developers, publishers, genres, and regions.  
* **`rom_file`**: Stores the unique hash and properties of a single digital file.  
* **`release_artifact`**: The crucial link between a `game_release` and a `rom_file`. This table models the physical media (cartridge, disc 1, etc.).

### **Section 3: Import & Validation Model (Enhanced in v1.7)**

These tables provide a unified, auditable log for all import activities and a staging area for DAT file contents with intelligent metadata parsing.

* **`metadata_source`**: A simple lookup for data providers, also provides the path to where their import script is located and the location of a schema file to validate files against.  
* **`import_log`**: A master log for every import job. It records the source file's name and hash, providing a single source of truth for all ingestions, an "undo" button for bad imports, and a mechanism to prevent processing the same file twice.  
* **`dat_entry` (Enhanced in v1.7)**: Stores a single entry from a DAT file import with intelligent parsing of universal metadata concepts:
  - **`release_title`**: Original full title from DAT file
  - **`base_title`**: Parsed clean title for atomic game matching (e.g., "Super Mario Bros." from "Super Mario Bros. (USA) (Rev 1)")  
  - **`region_normalized`**: Standardized region code (USA/EUR/JPN/World)
  - **`version_info`**: Parsed version information (v1.02, Rev 1, etc.)
  - **`development_status`**: Development status (demo, beta, proto, alpha, sample)
  - **`dump_status`**: Dump quality indicators (verified, good, bad, alternate, overdump, underdump)
  - **`language_codes`**: Standardized language codes (en, ja, fr, en-de, M3, etc.)
* **`dat_entry_metadata` (New in v1.7)**: Entity-Attribute-Value table for format-specific metadata that doesn't fit universal concepts:
  - **No-Intro specific**: aftermarket, digital_release, bios_flag, ntsc/pal indicators
  - **TOSEC specific**: publisher info, media labels, cracking group details
  - **GoodTools specific**: checksum info, ROM size, emulator tags, multicart details

### **Section 4: Operational Model \- File & Export Management**

These tables track the user's physical files and manage the process of creating versioned libraries and exporting them.

* **`library_root`**: Defines a root folder to be scanned (e.g., `C:\Users\Me\ROMs`).  
* **`file_instance`**: Represents the existence of a specific `rom_file` at a specific path within a `library_root`.  
* **`selection_policy`**: Defines the user's rules for 1G1R selection (e.g., region order `US > EU > JP`).  
* **`romset_version` & `romset_member`**: A version control system for your library. A `romset_version` is an immutable "snapshot" of the library based on a policy, with its contents defined in `romset_member`.  
* **`playlist` & `playlist_item`**: Allows for the creation of curated lists of games, linking to the `atomic_game_unit`.  
* **`target_device`, `export_profile`, `export_run`**: A system for defining export targets and the rules for how to structure the folders and files (`path_template`).

## **4\. DAT Metadata Parsing Architecture (New in v1.7)**

Version 1.7 introduces intelligent parsing of DAT file naming conventions to extract universal metadata concepts while preserving format-specific details.

### **Universal Metadata Extraction**

The system analyzes titles from major DAT formats (No-Intro, TOSEC, GoodTools) to extract common concepts:

**Example: No-Intro Format**  
`"Super Mario Bros. 3 (USA) (Rev 1) (Aftermarket) (Unl)"`  
→ Parsed as:
- `base_title`: "Super Mario Bros. 3"
- `region_normalized`: "USA"  
- `version_info`: "Rev 1"
- `dump_status`: "verified"
- Format-specific metadata: `aftermarket=true`, `unlicensed=true`

**Example: TOSEC Format**  
`"Super Mario Bros. 3 (1990)(Nintendo)(US)[cr PDX]"`  
→ Parsed as:
- `base_title`: "Super Mario Bros. 3"
- `region_normalized`: "USA"
- `dump_status`: "cracked"
- Format-specific metadata: `publisher=Nintendo`, `year=1990`, `cracked_by=PDX`

**Example: GoodTools Format**  
`"Super Mario Bros. 3 (U) [!]"`  
→ Parsed as:
- `base_title`: "Super Mario Bros. 3"
- `region_normalized`: "USA"  
- `dump_status`: "verified"

### **Hybrid Storage Strategy**

- **Core columns** in `dat_entry`: Store universal concepts for fast querying and atomic game matching
- **EAV table** `dat_entry_metadata`: Store format-specific oddities and unique attributes
- **Preservation**: Always keep original `release_title` for complete fidelity

This architecture enables:
1. **Fast atomic game matching** using normalized `base_title`
2. **Consistent 1G1R logic** using standardized `region_normalized` and `dump_status`
3. **Format preservation** for specialized use cases
4. **Extensibility** for future DAT formats

## **5\. Key Workflows**

### **Workflow 1: Importing & Reconciling Data (Updated for v1.7)**

1. **Initiate Import Job:** The user initiates an import of a MobyGames JSON file. The system calculates the file's SHA1 hash. If the hash already exists in `import_log`, the process stops. Otherwise, it creates a new `import_log` record with a status of 'running'.  
2. **Ingest Metadata:** The file is parsed. For each game, a new `atomic_game_unit` (if needed) and `game_release` are created. The core and extension metadata are populated in `atomic_core_metadata` and `atomic_metadata_extension`, with each record tagged with the new `log_id`.  
3. **Ingest & Parse No-Intro DAT:** A similar process runs for the DAT file, creating its own `import_log` entry. Each DAT entry is parsed to extract universal metadata (`base_title`, `region_normalized`, etc.) and format-specific details are stored in `dat_entry_metadata`.
4. **Intelligent Matching:** The application uses `base_title` from `dat_entry` to automatically link DAT entries to `atomic_game_unit`s, dramatically reducing manual curation work.
5. **Curation Prompt:** Remaining conflicts are flagged for user review, with suggested matches based on normalized titles.
6. **User Action & Reconciliation:** The user confirms or corrects automatic matches, and the system creates the appropriate `game_release` and `release_artifact` linkages.

### **Workflow 2: Creating & Exporting a 1G1R Romset (Enhanced with Parsed Metadata)**

1. **Define Policy:** The user creates a `selection_policy` that can now leverage parsed metadata (e.g., "USA > EUR > JPN, exclude demos and betas, prefer verified dumps").  
2. **Generate Version:** The user triggers the creation of a new `romset_version` based on the policy.  
3. **Enhanced Selection Logic:** The application uses parsed metadata from `dat_entry` for intelligent selection:
   - `region_normalized` for region preferences
   - `dump_status` to exclude bad dumps and prioritize verified ones
   - `development_status` to filter out demos/betas if desired
   - `version_info` to prefer latest revisions
4. **Populate Members:** The winning `atomic_id`, `chosen_release_id`, and `chosen_rom_id` are inserted into the `romset_member` table.  
5. **Export:** Export process remains the same but benefits from more intelligent ROM selection.

## **6\. Views Documentation (Updated for v1.7)**

The views provide simplified interfaces for common application queries, enhanced with parsed metadata.

### **Core Management Views**
* **`v_company_canonical`**: Resolves any company alias to its true canonical name.  
* **`v_romset_complete`**: Primary view for browsing versioned romset contents.  
* **`v_library_health`**: Shows local file collection status with ROM verification.  
* **`v_playlist_export_manifest`**: Provides file paths for playlist exports.  
* **`v_curation_todo`**: Dashboard for data integrity issues requiring attention.  

### **Enhanced DAT Analysis Views (New/Updated in v1.7)**
* **`v_dat_import_summary`**: Import statistics including parsing success rates
* **`v_dat_rom_matching`**: SHA1 matching with parsed metadata context
* **`v_dat_metadata_distribution`**: Analysis of parsed metadata across entries
* **`v_dat_format_specific_metadata`**: Usage statistics for format-specific attributes
* **`v_dat_atomic_linking_candidates`**: Intelligent suggestions for linking DAT entries to atomic games
* **`v_dat_clone_validation`**: Enhanced clone relationship analysis with parsed titles

## **7\. Migration from v1.6 to v1.7**

Existing databases can be migrated by:
1. Adding new columns to `dat_entry` table
2. Creating `dat_entry_metadata` table  
3. Running parsing routines on existing `release_title` data
4. Updating views and indexes

The migration preserves all existing data while adding the enhanced parsing capabilities.