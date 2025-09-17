# FAST database reseeding script using single transaction
# This recreates RomCurator.db much faster by using one big transaction

param(
    [string]$DatabasePath = ".\database\RomCurator.db"
)

Write-Host "ROM Curator FAST Database Reset & Seed" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# Remove existing database
if (Test-Path $DatabasePath) {
    Write-Host "Removing existing database..." -ForegroundColor Yellow
    Remove-Item $DatabasePath -Force
}

# Create fresh database with current schema
Write-Host "Creating fresh database with current schema..." -ForegroundColor Cyan
Get-Content "Rom Curator Database.sql" | sqlite3 $DatabasePath

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database created successfully" -ForegroundColor Green
} else {
    Write-Error "Failed to create database"
    exit 1
}

# Create one massive SQL file with all inserts in a single transaction
Write-Host "Building consolidated seed script..." -ForegroundColor Cyan

$consolidatedScript = @"
-- Single transaction for all seed data
PRAGMA synchronous = OFF;
PRAGMA journal_mode = MEMORY;
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

"@

# Add all INSERT statements in dependency order
$seedOrder = @(
    "01_metadata_source", "02_import_log", "03_platform", "04_genre", "05_company",
    "06_atomic_game_unit", "07_atomic_core_metadata", "08_atomic_metadata_extension", 
    "09_game_release", "10_release_developer", "11_release_publisher", "12_release_genre",
    "13_dat_entry", "14_dat_entry_metadata"
)

foreach ($table in $seedOrder) {
    $seedFile = ".\seed-scripts\inserts\$table.sql"
    if (Test-Path $seedFile) {
        Write-Host "  - Adding $table to batch..." -ForegroundColor Gray
        $consolidatedScript += "`n-- $table data`n"
        $consolidatedScript += Get-Content $seedFile -Raw
        $consolidatedScript += "`n"
    }
}

$consolidatedScript += @"

COMMIT;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = FULL;
PRAGMA journal_mode = DELETE;
ANALYZE;
"@

# Write to temp file and execute
$tempFile = [System.IO.Path]::GetTempFileName() + ".sql"
$consolidatedScript | Out-File -FilePath $tempFile -Encoding UTF8

Write-Host "Executing consolidated seed script (this should be much faster)..." -ForegroundColor Cyan
$startTime = Get-Date

Get-Content $tempFile | sqlite3 $DatabasePath

$endTime = Get-Date
$duration = $endTime - $startTime

# Cleanup
Remove-Item $tempFile -Force

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Seed data applied successfully in $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Green
} else {
    Write-Error "Failed to apply seed data"
    exit 1
}

# Final summary
Write-Host ""
Write-Host "Database reset completed!" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# Show final table counts
$tables = @("atomic_game_unit", "game_release", "dat_entry", "company", "platform", "genre")
foreach ($table in $tables) {
    $count = sqlite3 $DatabasePath "SELECT COUNT(*) FROM $table;"
    Write-Host "$table`: $count" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Your database is ready to use with all imported data!" -ForegroundColor Cyan
Write-Host "This approach uses a single transaction like the Python importers do." -ForegroundColor Yellow
