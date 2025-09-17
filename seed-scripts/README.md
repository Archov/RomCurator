# ROM Curator Database Seed Scripts

This directory contains seed scripts to quickly restore your database with all existing imported data, eliminating the need to re-import metadata every time the schema is updated.

## Files Created

- **Individual SQL Files (01-14)**: Exported data from each table in the correct dependency order
- **run_all_seeds.sql**: SQLite script that imports all seed files in sequence
- **seed_database.ps1**: PowerShell script that recreates database + seeds (Windows)  
- **seed_database.sh**: Bash script that recreates database + seeds (Linux/Mac)

## Quick Start

### Option 1: PowerShell (Windows)
```powershell
# Recreate database with fresh schema + seed data
.\seed-scripts\seed_database.ps1

# Or specify custom paths
.\seed-scripts\seed_database.ps1 -DatabasePath ".\database\MyDatabase.db" -SchemaFile ".\MySchema.sql"
```

### Option 2: Bash (Linux/Mac)
```bash
# Make script executable
chmod +x seed-scripts/seed_database.sh

# Recreate database with fresh schema + seed data
./seed-scripts/seed_database.sh

# Or specify custom paths
./seed-scripts/seed_database.sh "./database/MyDatabase.db" "./MySchema.sql"
```

### Option 3: Manual SQLite Commands
```bash
# Create fresh database with schema
sqlite3 database/RomCurator.db < "Rom Curator Database 1.7.sql"

# Apply seed data
sqlite3 database/RomCurator.db < seed-scripts/run_all_seeds.sql
```

### Option 4: Individual File Import
If you need to import specific tables only:
```bash
# Import just the core reference data
sqlite3 database/RomCurator.db < seed-scripts/01_metadata_source.sql
sqlite3 database/RomCurator.db < seed-scripts/03_platform.sql
sqlite3 database/RomCurator.db < seed-scripts/04_genre.sql
sqlite3 database/RomCurator.db < seed-scripts/05_company.sql

# Import atomic game data
sqlite3 database/RomCurator.db < seed-scripts/06_atomic_game_unit.sql
sqlite3 database/RomCurator.db < seed-scripts/07_atomic_core_metadata.sql

# etc...
```

## What Data is Included

The seed scripts preserve:

- **2,707 atomic game units** - Core game entities from MobyGames
- **9,617 game releases** - Platform-specific releases  
- **31,806 DAT entries** - ROM entries from No-Intro/TOSEC DATs
- **12,025 DAT metadata entries** - Format-specific metadata
- **1,433 companies** - Publishers/developers
- **185 genres** - Game categories
- **150 platforms** - Gaming systems
- **Import logs** - Track of what was imported when

## Troubleshooting

**Database locked errors**: 
- Close any open database connections (GUI apps, SQLite browsers)
- Try the manual SQLite approach instead

**Permission errors**:
- Ensure you have write access to the database directory
- Try running as administrator (Windows) or with sudo (Linux/Mac)

**Schema mismatches**:
- Ensure you're using the latest "Rom Curator Database 1.7.sql" schema
- The seed data was exported from v1.7 schema structures

## Regenerating Seed Scripts

If you need to regenerate the seed scripts from a different source database:

```bash
# Export each table (replace table_name with actual table)
sqlite3 source_database.db ".dump table_name" > seed-scripts/XX_table_name.sql

# Example for all major tables:
sqlite3 database/RomCurator.db ".dump metadata_source" > seed-scripts/01_metadata_source.sql
sqlite3 database/RomCurator.db ".dump platform" > seed-scripts/03_platform.sql
# ... etc for all tables with data
```

The scripts preserve all your imported MobyGames metadata, DAT entries, and relationships, so you can quickly get back to a fully populated state after any schema changes.
