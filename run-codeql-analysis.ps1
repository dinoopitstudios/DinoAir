# CodeQL Security Analysis Script for DinoAir
# Analyzes Python and JavaScript code for security vulnerabilities

Write-Host "CodeQL Security Analysis" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green

# Configuration
$projectPath = Get-Location
$databaseDir = "codeql-databases"
$resultsDir = "codeql-results"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

# Ensure CodeQL is in PATH
$codeqlPath = "C:\Users\DinoP\Documents\codeql-bundle-win64\codeql"
if (-not ($env:PATH -like "*$codeqlPath*")) {
    $env:PATH = "$codeqlPath;$env:PATH"
}

# Create directories
New-Item -ItemType Directory -Force -Path $databaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

Write-Host "Project: $projectPath" -ForegroundColor Cyan
Write-Host "Database directory: $databaseDir" -ForegroundColor Cyan
Write-Host "Results directory: $resultsDir" -ForegroundColor Cyan

# Function to run CodeQL analysis for a language
function Invoke-CodeQLAnalysis {
    param($Language, $DatabaseName)

    Write-Host "`nAnalyzing $Language code..." -ForegroundColor Yellow

    try {
        # Create database
        Write-Host "Creating $Language database..." -ForegroundColor Cyan
        & codeql database create "$databaseDir\$DatabaseName" --language="$Language" --source-root="$projectPath" --overwrite

        if ($LASTEXITCODE -eq 0) {
            Write-Host "Database created successfully" -ForegroundColor Green

            # Run analysis with security suite
            Write-Host "Running security analysis..." -ForegroundColor Cyan
            & codeql database analyze "$databaseDir\$DatabaseName" "codeql/$Language-queries" --format=sarif-latest --output="$resultsDir\$DatabaseName-security-$timestamp.sarif"

            if ($LASTEXITCODE -eq 0) {
                Write-Host "Analysis completed successfully" -ForegroundColor Green

                # Run additional code scanning queries
                Write-Host "Running code scanning queries..." -ForegroundColor Cyan
                & codeql database analyze "$databaseDir\$DatabaseName" "codeql/$Language-queries" --format=csv --output="$resultsDir\$DatabaseName-scanning-$timestamp.csv"

                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Code scanning completed" -ForegroundColor Green
                } else {
                    Write-Host "Code scanning failed (non-critical)" -ForegroundColor Yellow
                }

                return $true
            } else {
                Write-Host "Analysis failed" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "Database creation failed" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Error during $Language analysis: $_" -ForegroundColor Red
        return $false
    }
}

# Test CodeQL
Write-Host "`nTesting CodeQL installation..." -ForegroundColor Cyan
try {
    $version = & codeql version 2>&1
    Write-Host "CodeQL Version: $($version[0])" -ForegroundColor Green
} catch {
    Write-Host "CodeQL not found! Please ensure it's installed and in PATH" -ForegroundColor Red
    exit 1
}

# Languages to analyze
$languages = @(
    @{Language="python"; DatabaseName="dinoair-python"},
    @{Language="javascript"; DatabaseName="dinoair-javascript"}
)

$successCount = 0
$totalCount = $languages.Count

# Run analysis for each language
foreach ($config in $languages) {
    if (Invoke-CodeQLAnalysis -Language $config.Language -DatabaseName $config.DatabaseName) {
        $successCount++
    }
}

# Summary
Write-Host "`nAnalysis Summary" -ForegroundColor Green
Write-Host "================" -ForegroundColor Green
Write-Host "Successful analyses: $successCount/$totalCount" -ForegroundColor Cyan
Write-Host "Results saved to: $resultsDir" -ForegroundColor Cyan

if ($successCount -gt 0) {
    Write-Host "`nGenerated files:" -ForegroundColor Yellow
    Get-ChildItem $resultsDir -Name | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor White
    }

    Write-Host "`nTo view SARIF results:" -ForegroundColor Yellow
    Write-Host "1. Install SARIF Viewer extension in VS Code" -ForegroundColor White
    Write-Host "2. Open .sarif files to view security findings" -ForegroundColor White
    Write-Host "3. Check .csv files for detailed code scanning results" -ForegroundColor White
} else {
    Write-Host "No successful analyses completed" -ForegroundColor Red
}

Write-Host "`nDone!" -ForegroundColor Green