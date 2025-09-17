# Metadata + DAT Matching System Implementation Guide

This guide explains how to use the newly implemented metadata and DAT matching system to link imported game metadata with DAT entries.

## Overview

The matching system bridges the gap between:
- **Metadata sources** (MobyGames, etc.) that provide rich game information
- **DAT files** (No-Intro, TOSEC, etc.) that provide verified ROM information

By linking these together, you can create a comprehensive database that knows both the "what" (game metadata) and the "where" (ROM files).

## New Components

### 1. Enhanced DAT Parsing (`scripts/seeders/dat_parser.py`)
- Extracts universal metadata from DAT titles (base_title, region, version, etc.)
- Supports No-Intro, TOSEC, and GoodTools naming conventions
- Handles format-specific metadata

### 2. Matching Engine (`scripts/seeders/matching_engine.py`)
- Intelligent fuzzy matching between atomic games and DAT entries
- Confidence scoring and automatic linking
- Platform-aware matching

### 3. Curation GUI (`curation_gui.py`)
- Visual interface for manual review of potential matches
- Batch operations for high-confidence matches
- Skip and "no match" marking capabilities

### 4. Validation Tools (`scripts/validation/matching_validator.py`)
- Test suite for parser accuracy
- Database integrity checks
- Matching performance reports

## Setup Instructions

### 1. Database Schema Updates

The system requires the v1.7 database schema. If you're using an older schema, you'll need to add the enhanced columns:

```sql
-- Add enhanced parsing columns to dat_entry table
ALTER TABLE dat_entry ADD COLUMN base_title TEXT;
ALTER TABLE dat_entry ADD COLUMN region_normalized TEXT;
ALTER TABLE dat_entry ADD COLUMN version_info TEXT;
ALTER TABLE dat_entry ADD COLUMN development_status TEXT;
ALTER TABLE dat_entry ADD COLUMN dump_status TEXT DEFAULT 'unknown';
ALTER TABLE dat_entry ADD COLUMN language_codes TEXT;

-- Create dat_entry_metadata table for format-specific data
CREATE TABLE IF NOT EXISTS dat_entry_metadata (
    metadata_id INTEGER PRIMARY KEY,
    dat_entry_id INTEGER NOT NULL REFERENCES dat_entry(dat_entry_id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(dat_entry_id, key)
);

-- Create dat_atomic_link table for linking games to DAT entries
CREATE TABLE IF NOT EXISTS dat_atomic_link (
    link_id INTEGER PRIMARY KEY,
    atomic_id INTEGER NOT NULL REFERENCES atomic_game_unit(atomic_id),
    dat_entry_id INTEGER REFERENCES dat_entry(dat_entry_id),
    confidence REAL NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'manual',
    created_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(atomic_id, dat_entry_id)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_dat_entry_base_title ON dat_entry(base_title);
CREATE INDEX IF NOT EXISTS idx_dat_entry_platform ON dat_entry(platform_id);
CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_atomic ON dat_atomic_link(atomic_id);
CREATE INDEX IF NOT EXISTS idx_dat_atomic_link_dat ON dat_atomic_link(dat_entry_id);
```

### 2. Install Dependencies

The system requires the existing dependencies plus some additional packages:

```bash
pip install PyQt5>=5.15.0 qdarkstyle>=3.0.0 jsonschema>=4.0.0 lxml>=4.6.0
```

## Usage Workflow

### Step 1: Import Metadata and DAT Files

Use the existing import system to load your data:

1. **Import game metadata** (MobyGames, etc.)
   ```bash
   python data_importer_gui.py
   # Select your metadata source and JSON files
   ```

2. **Import DAT files** (No-Intro, TOSEC, etc.)
   ```bash
   python data_importer_gui.py
   # Select your DAT source and DAT files
   ```

### Step 2: Run Automatic Matching

```bash
cd scripts/seeders
python matching_engine.py --db_path ../../database/RomCurator.db --action create_table
python matching_engine.py --db_path ../../database/RomCurator.db --action auto_link
```

This will:
- Create the linking table
- Automatically link high-confidence matches (>95% confidence)
- Show statistics on what was linked

### Step 3: Manual Curation

For matches that need human review:

```bash
python curation_gui.py --db_path database/RomCurator.db
```

The curation interface allows you to:
- Review potential matches with confidence scores
- Manually approve or reject matches
- Mark games as having no matches
- Batch process high-confidence matches

### Step 4: Validation and Reports

Check the quality of your matches:

```bash
cd scripts/validation
python matching_validator.py --db_path ../../database/RomCurator.db --action validate
python matching_validator.py --db_path ../../database/RomCurator.db --action report --output matching_report.json
```

## Understanding the Matching Process

### Confidence Scores

The system assigns confidence scores (0.0 to 1.0) to potential matches:

- **0.95+**: High confidence, auto-linked
- **0.80-0.95**: Good matches, recommended for manual review
- **0.70-0.80**: Possible matches, may need careful review
- **<0.70**: Low confidence, likely false positives

### Matching Criteria

The engine considers:
1. **Title similarity** (exact, fuzzy, substring matches)
2. **Platform compatibility** (only matches within same platform)
3. **Normalized titles** (handles "The", Roman numerals, etc.)
4. **Word-order independence** (matches even if word order differs)

### Example Matches

Good automatic matches:
- "Super Mario Bros. 3" ↔ "Super Mario Bros. 3 (USA)"
- "Final Fantasy VI" ↔ "Final Fantasy 6 (Japan)"
- "Street Fighter II" ↔ "Street Fighter 2 - Champion Edition (World)"

Curation needed:
- "Final Fantasy III" ↔ "Final Fantasy 6 (Japan)" (regional numbering differences)
- "Game Title" ↔ "Game Title - Special Edition" (edition variations)

## Advanced Usage

### Custom Matching Rules

You can adjust matching behavior by modifying `matching_engine.py`:

```python
# Change confidence thresholds
high_confidence_threshold = 0.90  # Lower for more auto-linking
min_confidence = 0.60             # Lower to see more potential matches

# Modify title normalization
# Add patterns to GameMatcher.normalization_patterns
```

### Batch Operations

For large collections, use command-line tools:

```bash
# Show unmatched games
python matching_engine.py --db_path db.sqlite --action show_unmatched

# Show curation queue
python matching_engine.py --db_path db.sqlite --action show_curation --min_confidence 0.6

# Run validation and export results
python matching_validator.py --db_path db.sqlite --action validate --output validation_results.csv
```

### Integration with Existing Workflows

The matching system integrates with your existing workflow:

1. **Before matching**: Import metadata and DATs as usual
2. **After matching**: Proceed with 1G1R selection, library creation, exports
3. **Benefits**: Better ROM selection using combined metadata + DAT information

## Troubleshooting

### Common Issues

**"Table doesn't exist" errors**
- Run the database schema updates (Step 1)
- Ensure you're using the v1.7 schema

**No matches found**
- Check that you have both metadata and DAT entries for the same platforms
- Verify platform names match between sources
- Try lowering the minimum confidence threshold

**Poor match quality**
- Review the title normalization patterns
- Check for regional name differences (Final Fantasy III vs VI)
- Consider platform-specific naming conventions

### Performance Tips

- Run validation after major imports to check data quality
- Use automatic linking first, then manual curation
- Export reports periodically to track progress
- Consider platform-specific curation sessions

## Next Steps

Once you have good metadata-DAT linking:

1. **Enhanced 1G1R selection** using combined data
2. **Better ROM validation** against known good sets
3. **Improved export metadata** for target devices
4. **Smarter playlist creation** using rich metadata

The matching system provides the foundation for more intelligent ROM management based on both metadata richness and DAT validation.
