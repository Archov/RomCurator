# **Atomic Game Database \- Architecture Documentation v1.4**

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

## **3\. Schema Breakdown (v1.5)**

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

### **Section 3: Import & Validation Model**

These tables provide a unified, auditable log for all import activities and a staging area for DAT file contents.

* **`metadata_source`**: A simple lookup for data providers, also provides the path to where their import script is located (e.g., "MobyGames", "No-Intro").  
* **`import_log`**: A master log for every import job. It records the source file's name and hash, providing a single source of truth for all ingestions, an "undo" button for bad imports, and a mechanism to prevent processing the same file twice.  
* **`dat_entry`**: Stores a single, raw entry from a DAT file import, including the release title, SHA1 hash, and any parent/clone information. Each entry is linked directly to the `import_log` record for the DAT file it came from.

### **Section 4: Operational Model \- File & Export Management**

These tables track the user's physical files and manage the process of creating versioned libraries and exporting them.

* **`library_root`**: Defines a root folder to be scanned (e.g., `C:\Users\Me\ROMs`).  
* **`file_instance`**: Represents the existence of a specific `rom_file` at a specific path within a `library_root`.  
* **`selection_policy`**: Defines the user's rules for 1G1R selection (e.g., region order `US > EU > JP`).  
* **`romset_version` & `romset_member`**: A version control system for your library. A `romset_version` is an immutable "snapshot" of the library based on a policy, with its contents defined in `romset_member`.  
* **`playlist` & `playlist_item`**: Allows for the creation of curated lists of games, linking to the `atomic_game_unit`.  
* **`target_device`, `export_profile`, `export_run`**: A system for defining export targets and the rules for how to structure the folders and files (`path_template`).

## **4\. Key Workflows**

### **Workflow 1: Importing & Reconciling Data**

1. **Initiate Import Job:** The user initiates an import of a MobyGames JSON file. The system calculates the file's SHA1 hash. If the hash already exists in `import_log`, the process stops. Otherwise, it creates a new `import_log` record with a status of 'running'.  
2. **Ingest Metadata:** The file is parsed. For each game, a new `atomic_game_unit` (if needed) and `game_release` are created. The core and extension metadata are populated in `atomic_core_metadata` and `atomic_metadata_extension`, with each record tagged with the new `log_id`.  
3. **Ingest No-Intro DAT:** A similar process runs for the DAT file, creating its own `import_log` entry and populating `dat_entry`.  
4. **Curation Prompt:** The application queries for `dat_entry` records with the same `clone_of` value. Seeing that they point to different `atomic_game_unit`s, it flags a conflict.  
5. **User Action & Reconciliation:** The user is prompted to select the correct canonical title for the group (e.g., "Final Fantasy VI"). The system then updates the `atomic_id` on the incorrect `game_release` record to point to the correct `atomic_game_unit`.

### **Workflow 2: Creating & Exporting a 1G1R Romset**

1. **Define Policy:** The user creates a `selection_policy` (e.g., "USA Preferred").  
2. **Generate Version:** The user triggers the creation of a new `romset_version` based on the policy.  
3. **Selection Logic:** The application iterates through every `atomic_game_unit`, finds all associated `game_release`s, and applies the policy rules to find the single best `rom_file`.  
4. **Populate Members:** The winning `atomic_id`, `chosen_release_id`, and `chosen_rom_id` are inserted into the `romset_member` table, linked to the `version_id`.  
5. **Export:** The user selects the `romset_version` and an `export_profile`. The application queries `romset_member`, joins with `file_instance` to find the physical file paths, and copies them to the destination.

## **5\. Views Documentation (Conceptual)**

The views (to be created) will provide a simplified interface for common application queries.

* **`v_company_canonical`**: A critical view that resolves any company alias to its true canonical name.  
* **`v_romset_complete`**: The primary view for browsing the contents of a finished, versioned romset.  
* **`v_library_health`**: Shows the user the status of their local file collection—which files are verified, which are not, and which games they correspond to.  
* **`v_playlist_export_manifest`**: Provides the exact list of source file paths needed to build a playlist export for a given romset version.  
* **`v_curation_todo`**: A dashboard that points out data integrity issues requiring manual attention, such as unresolved clone sets or imported games not yet linked to a verified ROM.  
* 