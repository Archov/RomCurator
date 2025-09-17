# =============================================================================
# ROM CURATOR DATABASE SEEDING SCRIPT
# =============================================================================
# This PowerShell script recreates the database with schema and seeds it with data
# Usage: .\seed-scripts\seed_database.ps1

param(
    [string]$DatabasePath = ".\database\RomCurator.db",
    [string]$SchemaFile = ".\Rom Curator Database 1.7.sql"
)

Write-Host "ROM Curator Database Seeding Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Check if schema file exists
if (-not (Test-Path $SchemaFile)) {
    Write-Error "Schema file not found: $SchemaFile"
    exit 1
}

# Check if seed scripts directory exists
if (-not (Test-Path ".\seed-scripts")) {
    Write-Error "Seed scripts directory not found: .\seed-scripts"
    exit 1
}

# Create database directory if it doesn't exist
$dbDir = Split-Path $DatabasePath -Parent
if (-not (Test-Path $dbDir)) {
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
    Write-Host "Created database directory: $dbDir" -ForegroundColor Yellow
}

# Remove existing database if it exists
if (Test-Path $DatabasePath) {
    Write-Host "Removing existing database: $DatabasePath" -ForegroundColor Yellow
    Remove-Item $DatabasePath -Force
}

# Create new database with schema
Write-Host "Creating database with schema..." -ForegroundColor Cyan
Get-Content $SchemaFile | sqlite3 $DatabasePath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create database schema"
    exit 1
}

Write-Host "Schema created successfully" -ForegroundColor Green

# Apply seed data in correct order
$seedFiles = @(
    "01_metadata_source.sql",
    "02_import_log.sql", 
    "03_platform.sql",
    "04_genre.sql",
    "05_company.sql",
    "06_atomic_game_unit.sql",
    "07_atomic_core_metadata.sql",
    "08_atomic_metadata_extension.sql",
    "09_game_release.sql",
    "10_release_developer.sql",
    "11_release_publisher.sql",
    "12_release_genre.sql",
    "13_dat_entry.sql",
    "14_dat_entry_metadata.sql"
)

Write-Host "Applying seed data..." -ForegroundColor Cyan

foreach ($seedFile in $seedFiles) {
    $fullPath = ".\seed-scripts\$seedFile"
    if (Test-Path $fullPath) {
        Write-Host "  - Loading $seedFile" -ForegroundColor White
        
        # Read the file and extract only INSERT statements
        $content = Get-Content $fullPath | Where-Object { 
            $_ -match "^INSERT" -or $_ -match "^PRAGMA"
        }
        
        if ($content) {
            $content | sqlite3 $DatabasePath
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Warning: Some errors occurred loading $seedFile"
            }
        }
    } else {
        Write-Warning "Seed file not found: $fullPath"
    }
}

# Get final row counts
Write-Host ""
Write-Host "Seeding completed! Final row counts:" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

$tables = @("metadata_source", "platform", "genre", "company", "atomic_game_unit", "game_release", "dat_entry", "dat_entry_metadata")

foreach ($table in $tables) {
    $count = sqlite3 $DatabasePath "SELECT COUNT(*) FROM $table;"
    Write-Host "$table`: $count" -ForegroundColor White
}

Write-Host ""
Write-Host "Database seeding completed successfully!" -ForegroundColor Green
Write-Host "You can now use the seeded database: $DatabasePath" -ForegroundColor Cyan
