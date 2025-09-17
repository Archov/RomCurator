#!/bin/bash
# =============================================================================
# ROM CURATOR DATABASE SEEDING SCRIPT
# =============================================================================
# This script recreates the database with schema and seeds it with data
# Usage: ./seed-scripts/seed_database.sh

DATABASE_PATH="${1:-./database/RomCurator.db}"
SCHEMA_FILE="${2:-./Rom Curator Database 1.7.sql}"

echo "ROM Curator Database Seeding Script"
echo "===================================="

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Error: Schema file not found: $SCHEMA_FILE"
    exit 1
fi

# Check if seed scripts directory exists
if [ ! -d "./seed-scripts" ]; then
    echo "Error: Seed scripts directory not found: ./seed-scripts"
    exit 1
fi

# Create database directory if it doesn't exist
DB_DIR=$(dirname "$DATABASE_PATH")
if [ ! -d "$DB_DIR" ]; then
    mkdir -p "$DB_DIR"
    echo "Created database directory: $DB_DIR"
fi

# Remove existing database if it exists
if [ -f "$DATABASE_PATH" ]; then
    echo "Removing existing database: $DATABASE_PATH"
    rm -f "$DATABASE_PATH"
fi

# Create new database with schema
echo "Creating database with schema..."
sqlite3 "$DATABASE_PATH" < "$SCHEMA_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create database schema"
    exit 1
fi

echo "Schema created successfully"

# Apply seed data in correct order
SEED_FILES=(
    "01_metadata_source.sql"
    "02_import_log.sql" 
    "03_platform.sql"
    "04_genre.sql"
    "05_company.sql"
    "06_atomic_game_unit.sql"
    "07_atomic_core_metadata.sql"
    "08_atomic_metadata_extension.sql"
    "09_game_release.sql"
    "10_release_developer.sql"
    "11_release_publisher.sql"
    "12_release_genre.sql"
    "13_dat_entry.sql"
    "14_dat_entry_metadata.sql"
)

echo "Applying seed data..."

for SEED_FILE in "${SEED_FILES[@]}"; do
    FULL_PATH="./seed-scripts/$SEED_FILE"
    if [ -f "$FULL_PATH" ]; then
        echo "  - Loading $SEED_FILE"
        
        # Extract only INSERT statements and apply them
        grep "^INSERT\|^PRAGMA" "$FULL_PATH" | sqlite3 "$DATABASE_PATH"
        if [ $? -ne 0 ]; then
            echo "Warning: Some errors occurred loading $SEED_FILE"
        fi
    else
        echo "Warning: Seed file not found: $FULL_PATH"
    fi
done

# Get final row counts
echo ""
echo "Seeding completed! Final row counts:"
echo "===================================="

TABLES=("metadata_source" "platform" "genre" "company" "atomic_game_unit" "game_release" "dat_entry" "dat_entry_metadata")

for TABLE in "${TABLES[@]}"; do
    COUNT=$(sqlite3 "$DATABASE_PATH" "SELECT COUNT(*) FROM $TABLE;")
    echo "$TABLE: $COUNT"
done

echo ""
echo "Database seeding completed successfully!"
echo "You can now use the seeded database: $DATABASE_PATH"
