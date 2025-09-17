# Script to extract only INSERT statements from dump files
param(
    [string]$InputDir = ".\seed-scripts",
    [string]$OutputDir = ".\seed-scripts\inserts"
)

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Process each SQL file
$sqlFiles = Get-ChildItem "$InputDir\*.sql" | Where-Object { $_.Name -match "^\d{2}_.*\.sql$" }

foreach ($file in $sqlFiles) {
    Write-Host "Processing $($file.Name)..."
    
    # Read file and extract only INSERT statements
    $content = Get-Content $file.FullName | Where-Object { 
        $_ -match "^INSERT INTO" 
    }
    
    if ($content) {
        $outputFile = Join-Path $OutputDir $file.Name
        $content | Out-File -FilePath $outputFile -Encoding UTF8
        Write-Host "  Created $($file.Name) with $(($content | Measure-Object).Count) INSERT statements"
    } else {
        Write-Host "  No INSERT statements found in $($file.Name)"
    }
}

Write-Host "Extraction completed!"
