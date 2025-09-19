# CodeQL Workflow Cleanup Script
# This script finds and cleans up any duplicate or problematic CodeQL workflow files

Write-Host "CodeQL Workflow Cleanup" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

$workflowsDir = ".github/workflows"
$configDir = ".github/codeql"

Write-Host "`nChecking for CodeQL workflow files..." -ForegroundColor Cyan

# Find all files with codeql in the name
$codeqlFiles = Get-ChildItem -Path . -Recurse -Force | Where-Object {
    $_.Name -like "*codeql*" -and
    ($_.Extension -eq ".yml" -or $_.Extension -eq ".yaml")
}

Write-Host "Found CodeQL workflow files:" -ForegroundColor Yellow
foreach ($file in $codeqlFiles) {
    $relativePath = $file.FullName.Replace((Get-Location).Path, ".")
    $size = $file.Length
    Write-Host "  - $relativePath ($size bytes)" -ForegroundColor White
}

# Check for empty or duplicate files
Write-Host "`nChecking for empty or problematic files..." -ForegroundColor Cyan
$emptyFiles = $codeqlFiles | Where-Object { $_.Length -eq 0 }
$duplicateNames = $codeqlFiles | Group-Object Name | Where-Object { $_.Count -gt 1 }

if ($emptyFiles) {
    Write-Host "Found empty files:" -ForegroundColor Red
    foreach ($file in $emptyFiles) {
        Write-Host "  - $($file.FullName)" -ForegroundColor Red
        $confirm = Read-Host "Delete empty file? (y/N)"
        if ($confirm -eq "y" -or $confirm -eq "Y") {
            Remove-Item $file.FullName -Force
            Write-Host "    Deleted!" -ForegroundColor Green
        }
    }
} else {
    Write-Host "No empty files found." -ForegroundColor Green
}

if ($duplicateNames) {
    Write-Host "Found duplicate filenames:" -ForegroundColor Yellow
    foreach ($group in $duplicateNames) {
        Write-Host "  Filename: $($group.Name)" -ForegroundColor Yellow
        foreach ($file in $group.Group) {
            Write-Host "    - $($file.FullName) ($($file.Length) bytes)" -ForegroundColor White
        }
    }
} else {
    Write-Host "No duplicate filenames found." -ForegroundColor Green
}

# Verify the correct file exists
$correctFile = Join-Path $workflowsDir "codeql-analysis.yml"
if (Test-Path $correctFile) {
    $size = (Get-Item $correctFile).Length
    Write-Host "`nCorrect CodeQL workflow file exists:" -ForegroundColor Green
    Write-Host "  Path: $correctFile" -ForegroundColor White
    Write-Host "  Size: $size bytes" -ForegroundColor White

    # Check if it contains v3 actions
    $content = Get-Content $correctFile -Raw
    if ($content -match "github/codeql-action.*@v3") {
        Write-Host "  Version: Updated to v3 ✅" -ForegroundColor Green
    } else {
        Write-Host "  Version: Needs v3 update ⚠️" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nWARNING: CodeQL workflow file missing!" -ForegroundColor Red
}

Write-Host "`nCleanup complete!" -ForegroundColor Green