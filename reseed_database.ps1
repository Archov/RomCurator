# Simple database reseeding script
# This recreates RomCurator.db from scratch with the v1.7 schema and all existing data

param(
    [string]$DatabasePath = ".\database\RomCurator.db"
)

Write-Host "ROM Curator Database Reset & Seed" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Remove existing database
if (Test-Path $DatabasePath) {
    Write-Host "Removing existing database..." -ForegroundColor Yellow
    Remove-Item $DatabasePath -Force
}

# Create fresh database with v1.7 schema
Write-Host "Creating fresh database with v1.7 schema..." -ForegroundColor Cyan
Get-Content "Rom Curator Database 1.7.sql" | sqlite3 $DatabasePath

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database created successfully" -ForegroundColor Green
} else {
    Write-Error "Failed to create database"
    exit 1
}

# Apply seed data in correct order using INSERT-only files
Write-Host "Applying seed data..." -ForegroundColor Cyan

$seedOrder = @(
    "01_metadata_source", "02_import_log", "03_platform", "04_genre", "05_company",
    "06_atomic_game_unit", "07_atomic_core_metadata", "08_atomic_metadata_extension",
    "09_game_release", "10_release_developer", "11_release_publisher", "12_release_genre",
    "13_dat_entry", "14_dat_entry_metadata"
)

$totalInserted = 0

foreach ($table in $seedOrder) {
    $seedFile = ".\seed-scripts\inserts\$table.sql"
    if (Test-Path $seedFile) {
        Write-Host "  - Loading $table..." -ForegroundColor White
        Get-Content $seedFile | sqlite3 $DatabasePath
        
        if ($LASTEXITCODE -eq 0) {
            $count = sqlite3 $DatabasePath "SELECT COUNT(*) FROM $($table.Substring(3));"
            Write-Host "    ✓ $count rows" -ForegroundColor Gray
            $totalInserted += [int]$count
        } else {
            Write-Warning "Some errors occurred loading $table"
        }
    } else {
        Write-Warning "Seed file not found: $seedFile"
    }
}

# Final summary
Write-Host ""
Write-Host "Database reset completed!" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host "Total records inserted: $totalInserted" -ForegroundColor White

# Show final table counts
$tables = @("atomic_game_unit", "game_release", "dat_entry", "company", "platform", "genre")
foreach ($table in $tables) {
    $count = sqlite3 $DatabasePath "SELECT COUNT(*) FROM $table;"
    Write-Host "$table`: $count" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Your database is ready to use with all imported data!" -ForegroundColor Cyan
