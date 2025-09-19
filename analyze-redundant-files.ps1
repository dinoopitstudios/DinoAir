# Repository Cleanup Analysis Script# Repository Cleanup Analysis Script# Repository Cleanup Analysis Script

# Identifies redundant, obsolete, and unneeded files in the DinoAir repository root

# Identifies redundant, obsolete, and unneeded files in the DinoAir repository root# Identifies redundant, obsolete, and unneeded files in the DinoAir repository root

Write-Host "DinoAir Repository Cleanup Analysis" -ForegroundColor Green

Write-Host "==================================" -ForegroundColor Green



$rootPath = "."Write-Host "DinoAir Repository Cleanup Analysis" -ForegroundColor GreenWrite-Host "DinoAir Repository Cleanup Analysis" -ForegroundColor Green



# Get all files in root (excluding directories)Write-Host "==================================" -ForegroundColor GreenWrite-Host "==================================" -ForegroundColor Green

$allFiles = Get-ChildItem $rootPath -File | Sort-Object Name



Write-Host ""

Write-Host "Analyzing $($allFiles.Count) files in repository root..." -ForegroundColor Cyan$rootPath = "."$rootPath = "."



# Categorize potentially redundant files$potentiallyRedundant = @()

Write-Host ""

Write-Host "POTENTIALLY REDUNDANT FILES:" -ForegroundColor Yellow# Get all files in root (excluding directories)$definitelyRedundant = @()

Write-Host "=============================" -ForegroundColor Yellow

$allFiles = Get-ChildItem $rootPath -File | Sort-Object Name$temporary = @()

# Check for multiple demo files

$demoFiles = $allFiles | Where-Object { $_.Name -like "*demo*" }$documentation = @()

if ($demoFiles.Count -gt 0) {

    Write-Host ""Write-Host "`nAnalyzing $($allFiles.Count) files in repository root..." -ForegroundColor Cyan$backups = @()

    Write-Host "DEMO FILES (multiple versions found):" -ForegroundColor Red

    foreach ($file in $demoFiles) {

        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")

        Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White# Categorize potentially redundant files# Get all files in root (excluding directories)

    }

}Write-Host "`nPOTENTIALLY REDUNDANT FILES:" -ForegroundColor Yellow$allFiles = Get-ChildItem $rootPath -File | Sort-Object Name



# Check for multiple API tracker filesWrite-Host "=============================" -ForegroundColor Yellow

$apiTrackerFiles = $allFiles | Where-Object { $_.Name -like "*api-tracker*" -or $_.Name -like "*tracker*" }

if ($apiTrackerFiles.Count -gt 0) {Write-Host "`nAnalyzing $($allFiles.Count) files in repository root..." -ForegroundColor Cyan

    Write-Host ""

    Write-Host "API TRACKER FILES (multiple versions found):" -ForegroundColor Red# Check for multiple demo files

    foreach ($file in $apiTrackerFiles) {

        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")$demoFiles = $allFiles | Where-Object { $_.Name -like "*demo*" }# Categorize files

        Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White

    }if ($demoFiles.Count -gt 0) {foreach ($file in $allFiles) {

}

    Write-Host "`nDEMO FILES (multiple versions found):" -ForegroundColor Red    $name = $file.Name

# Check for multiple mypy config files

$mypyFiles = $allFiles | Where-Object { $_.Name -like "*mypy*" }    foreach ($file in $demoFiles) {    $extension = $file.Extension

if ($mypyFiles.Count -gt 0) {

    Write-Host ""        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")    $size = $file.Length

    Write-Host "MYPY CONFIG FILES (multiple configs found):" -ForegroundColor Red

    foreach ($file in $mypyFiles) {        Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }    }    # Temporary/cache files

}

}    if ($name -like "*.tmp" -or $name -like "*.temp" -or $name -like "*.cache" -or

# Check for archive files

$archiveFiles = $allFiles | Where-Object { $_.Extension -eq ".zip" -or $_.Extension -eq ".tar" -or $_.Extension -eq ".gz" }        $name -like "*.log" -or $extension -eq ".pyc") {

if ($archiveFiles.Count -gt 0) {

    Write-Host ""# Check for multiple API tracker files        $temporary += @{File=$name; Reason="Temporary/cache file"; Size=$size}

    Write-Host "ARCHIVE FILES (may be temporary):" -ForegroundColor Yellow

    foreach ($file in $archiveFiles) {$apiTrackerFiles = $allFiles | Where-Object { $_.Name -like "*api-tracker*" -or $_.Name -like "*tracker*" }    }

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }if ($apiTrackerFiles.Count -gt 0) {

}

    Write-Host "`nAPI TRACKER FILES (multiple versions found):" -ForegroundColor Red    # Backup files

# Check for standalone test/validation scripts

$testFiles = $allFiles | Where-Object { $_.Name -like "check_*" -or $_.Name -like "test_*" -or $_.Name -like "validate_*" -or $_.Name -like "test-*" }    foreach ($file in $apiTrackerFiles) {    elseif ($name -like "*.backup" -or $name -like "*.bak" -or $name -like "*.orig" -or

if ($testFiles.Count -gt 0) {

    Write-Host ""        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")            $name -like "*~" -or $name -like "*.old") {

    Write-Host "STANDALONE TEST/VALIDATION SCRIPTS:" -ForegroundColor Yellow

    foreach ($file in $testFiles) {        Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White        $backups += @{File=$name; Reason="Backup file"; Size=$size}

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }    }    }

}

}

# Check for utility/cleanup scripts

$utilityFiles = $allFiles | Where-Object { $_.Name -like "remove_*" -or $_.Name -like "cleanup*" -or $_.Name -like "migrate_*" -or $_.Name -like "fix*" -or $_.Name -like "manage_*" }    # Multiple similar files (potential duplicates)

if ($utilityFiles.Count -gt 0) {

    Write-Host ""# Check for multiple mypy config files    elseif ($name -like "*demo*" -and $extension -eq ".cjs") {

    Write-Host "UTILITY/CLEANUP SCRIPTS (may be one-time use):" -ForegroundColor Yellow

    foreach ($file in $utilityFiles) {$mypyFiles = $allFiles | Where-Object { $_.Name -like "*mypy*" }        $potentiallyRedundant += @{File=$name; Reason="Multiple demo files - may be outdated"; Size=$size}

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }if ($mypyFiles.Count -gt 0) {    }

}

    Write-Host "`nMYPY CONFIG FILES (multiple configs found):" -ForegroundColor Red    elseif ($name -like "*api-tracker*" -and ($extension -eq ".js" -or $extension -eq ".cjs")) {

# Check for backup/old files

$oldFiles = $allFiles | Where-Object { $_.Name -like "*.old" -or $_.Name -like "*.backup" -or $_.Name -like "*.bak" }    foreach ($file in $mypyFiles) {        $potentiallyRedundant += @{File=$name; Reason="Multiple API tracker files - consolidation needed"; Size=$size}

if ($oldFiles.Count -gt 0) {

    Write-Host ""        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White    }

    Write-Host "BACKUP/OLD FILES:" -ForegroundColor Red

    foreach ($file in $oldFiles) {    }    elseif ($name -like "*mypy*") {

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }}        $potentiallyRedundant += @{File=$name; Reason="Multiple mypy config files"; Size=$size}

}

    }

# Check for multiple HTML files

$htmlFiles = $allFiles | Where-Object { $_.Extension -eq ".html" }# Check for multiple activation scripts    elseif ($name -like "*activate*" -and $extension -eq ".ps1") {

if ($htmlFiles.Count -gt 1) {

    Write-Host ""$activationFiles = $allFiles | Where-Object { $_.Name -like "*activate*" }        $potentiallyRedundant += @{File=$name; Reason="Multiple activation scripts"; Size=$size}

    Write-Host "HTML FILES (check if all needed):" -ForegroundColor Yellow

    foreach ($file in $htmlFiles) {if ($activationFiles.Count -gt 0) {    }

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }    Write-Host "`nACTIVATION SCRIPTS (multiple versions found):" -ForegroundColor Red

}

    foreach ($file in $activationFiles) {    # Test/validation files that might be obsolete

# Check for requirements files

$reqFiles = $allFiles | Where-Object { $_.Name -like "requirements*" }        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White    elseif ($name -like "check_*" -or $name -like "test_*" -or $name -like "validate_*") {

if ($reqFiles.Count -gt 0) {

    Write-Host ""    }        $potentiallyRedundant += @{File=$name; Reason="Standalone test/validation script"; Size=$size}

    Write-Host "REQUIREMENTS FILES:" -ForegroundColor Cyan

    foreach ($file in $reqFiles) {}    }

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White

    }

}

# Check for archive files    # Archive/zip files (usually temporary)

# Check for models.py vs models/ directory conflict

$modelsFile = $allFiles | Where-Object { $_.Name -eq "models.py" }$archiveFiles = $allFiles | Where-Object { $_.Extension -eq ".zip" -or $_.Extension -eq ".tar" -or $_.Extension -eq ".gz" }    elseif ($extension -eq ".zip" -or $extension -eq ".tar" -or $extension -eq ".gz") {

$modelsDir = Get-ChildItem $rootPath -Directory | Where-Object { $_.Name -eq "models" }

if ($modelsFile -and $modelsDir) {if ($archiveFiles.Count -gt 0) {        $potentiallyRedundant += @{File=$name; Reason="Archive file - may be temporary"; Size=$size}

    Write-Host ""

    Write-Host "MODELS CONFLICT (both file and directory exist):" -ForegroundColor Red    Write-Host "`nARCHIVE FILES (may be temporary):" -ForegroundColor Yellow    }

    Write-Host "  - models.py (file: $($modelsFile.Length) bytes)" -ForegroundColor White

    Write-Host "  - models/ (directory)" -ForegroundColor White    foreach ($file in $archiveFiles) {

}

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White    # Documentation files (review for redundancy)

Write-Host ""

Write-Host "DOCUMENTATION FILES (review for current relevance):" -ForegroundColor Cyan    }    elseif ($extension -eq ".md" -and $name -notlike "README*") {

$docFiles = $allFiles | Where-Object { $_.Extension -eq ".md" -and $_.Name -notlike "README*" }

foreach ($file in $docFiles) {}        $documentation += @{File=$name; Reason="Documentation file - review for relevance"; Size=$size}

    $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")

    Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White    }

}

# Check for standalone test/validation scripts

Write-Host ""

Write-Host "RECOMMENDATIONS:" -ForegroundColor Green$testFiles = $allFiles | Where-Object { $_.Name -like "check_*" -or $_.Name -like "test_*" -or $_.Name -like "validate_*" -or $_.Name -like "test-*" }    # Potentially obsolete scripts

Write-Host "================" -ForegroundColor Green

Write-Host "1. Consolidate demo files - keep only the latest working version" -ForegroundColor Whiteif ($testFiles.Count -gt 0) {    elseif ($name -like "remove_*" -or $name -like "cleanup*" -or $name -like "migrate_*") {

Write-Host "2. Merge API tracker files or choose the primary one" -ForegroundColor White

Write-Host "3. Review mypy configs - typically need only one" -ForegroundColor White    Write-Host "`nSTANDALONE TEST/VALIDATION SCRIPTS:" -ForegroundColor Yellow        $potentiallyRedundant += @{File=$name; Reason="Utility script - may be one-time use"; Size=$size}

Write-Host "4. Remove or move archive files to appropriate location" -ForegroundColor White

Write-Host "5. Move utility scripts to scripts/ directory" -ForegroundColor White    foreach ($file in $testFiles) {    }

Write-Host "6. Review documentation files for current relevance" -ForegroundColor White

Write-Host "7. Consider removing standalone test files if covered by proper test suite" -ForegroundColor White        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White



Write-Host ""    }    # Development/build artifacts

Write-Host "Analysis complete!" -ForegroundColor Green
}    elseif ($name -like "*.egg-info" -or $name -like "build" -or $name -like "dist") {

        $definitelyRedundant += @{File=$name; Reason="Build artifact - should be in .gitignore"; Size=$size}

# Check for utility/cleanup scripts    }

$utilityFiles = $allFiles | Where-Object { $_.Name -like "remove_*" -or $_.Name -like "cleanup*" -or $_.Name -like "migrate_*" -or $_.Name -like "fix*" -or $_.Name -like "manage_*" }}

if ($utilityFiles.Count -gt 0) {

    Write-Host "`nUTILITY/CLEANUP SCRIPTS (may be one-time use):" -ForegroundColor Yellow# Display results

    foreach ($file in $utilityFiles) {Write-Host "`n🗑️  DEFINITELY REDUNDANT (Safe to remove):" -ForegroundColor Red

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor Whiteif ($definitelyRedundant.Count -eq 0) {

    }    Write-Host "  None found ✅" -ForegroundColor Green

}} else {

    foreach ($item in $definitelyRedundant) {

# Check for old/outdated files        Write-Host "  ❌ $($item.File) - $($item.Reason) ($($item.Size) bytes)" -ForegroundColor Red

$oldFiles = $allFiles | Where-Object { $_.Name -like "*.old" -or $_.Name -like "*.backup" -or $_.Name -like "*.bak" }    }

if ($oldFiles.Count -gt 0) {}

    Write-Host "`nBACKUP/OLD FILES:" -ForegroundColor Red

    foreach ($file in $oldFiles) {Write-Host "`n⚠️  TEMPORARY/CACHE FILES:" -ForegroundColor Yellow

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor Whiteif ($temporary.Count -eq 0) {

    }    Write-Host "  None found ✅" -ForegroundColor Green

}} else {

    foreach ($item in $temporary) {

# Check for specific redundant files        Write-Host "  🧹 $($item.File) - $($item.Reason) ($($item.Size) bytes)" -ForegroundColor Yellow

$specificRedundant = @()    }

}

# Multiple HTML files

$htmlFiles = $allFiles | Where-Object { $_.Extension -eq ".html" }Write-Host "`n💾 BACKUP FILES:" -ForegroundColor Magenta

if ($htmlFiles.Count -gt 1) {if ($backups.Count -eq 0) {

    Write-Host "`nHTML FILES (check if all needed):" -ForegroundColor Yellow    Write-Host "  None found ✅" -ForegroundColor Green

    foreach ($file in $htmlFiles) {} else {

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White    foreach ($item in $backups) {

    }        Write-Host "  📁 $($item.File) - $($item.Reason) ($($item.Size) bytes)" -ForegroundColor Magenta

}    }

}

# Check for requirements files

$reqFiles = $allFiles | Where-Object { $_.Name -like "requirements*" }Write-Host "`n❓ POTENTIALLY REDUNDANT (Review needed):" -ForegroundColor Yellow

if ($reqFiles.Count -gt 0) {if ($potentiallyRedundant.Count -eq 0) {

    Write-Host "`nREQUIREMENTS FILES:" -ForegroundColor Cyan    Write-Host "  None found ✅" -ForegroundColor Green

    foreach ($file in $reqFiles) {} else {

        Write-Host "  - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White    foreach ($item in $potentiallyRedundant) {

    }        Write-Host "  📋 $($item.File) - $($item.Reason) ($($item.Size) bytes)" -ForegroundColor Yellow

}    }

}

# Check for models.py vs models/ directory conflict

$modelsFile = $allFiles | Where-Object { $_.Name -eq "models.py" }Write-Host "`n📚 DOCUMENTATION FILES (Review for relevance):" -ForegroundColor Cyan

$modelsDir = Get-ChildItem $rootPath -Directory | Where-Object { $_.Name -eq "models" }foreach ($item in $documentation) {

if ($modelsFile -and $modelsDir) {    Write-Host "  📄 $($item.File) - $($item.Reason) ($($item.Size) bytes)" -ForegroundColor Cyan

    Write-Host "`nMODELS CONFLICT (both file and directory exist):" -ForegroundColor Red}

    Write-Host "  - models.py (file: $($modelsFile.Length) bytes)" -ForegroundColor White

    Write-Host "  - models/ (directory)" -ForegroundColor White# Specific analysis for common patterns

}Write-Host "`n🔍 DETAILED ANALYSIS:" -ForegroundColor Green



Write-Host "`nDOCUMENTATION FILES (review for current relevance):" -ForegroundColor Cyan# Check for multiple similar files

$docFiles = $allFiles | Where-Object { $_.Extension -eq ".md" -and $_.Name -notlike "README*" }$demoFiles = $allFiles | Where-Object { $_.Name -like "*demo*" }

foreach ($file in $docFiles) {if ($demoFiles.Count -gt 1) {

    $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")    Write-Host "`n  Multiple demo files found:" -ForegroundColor Yellow

    Write-Host "  - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White    foreach ($file in $demoFiles) {

}        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")

        Write-Host "    - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White

Write-Host "`nRECOMMENDATIONS:" -ForegroundColor Green    }

Write-Host "================" -ForegroundColor Green}

Write-Host "1. Consolidate demo files - keep only the latest working version" -ForegroundColor White

Write-Host "2. Merge API tracker files or choose the primary one" -ForegroundColor White$apiTrackerFiles = $allFiles | Where-Object { $_.Name -like "*api-tracker*" }

Write-Host "3. Review mypy configs - typically need only one" -ForegroundColor Whiteif ($apiTrackerFiles.Count -gt 1) {

Write-Host "4. Keep only one activation script" -ForegroundColor White    Write-Host "`n  Multiple API tracker files found:" -ForegroundColor Yellow

Write-Host "5. Remove or move archive files to appropriate location" -ForegroundColor White    foreach ($file in $apiTrackerFiles) {

Write-Host "6. Move utility scripts to scripts/ directory" -ForegroundColor White        $lastModified = $file.LastWriteTime.ToString("yyyy-MM-dd")

Write-Host "7. Review documentation files for current relevance" -ForegroundColor White        Write-Host "    - $($file.Name) (modified: $lastModified, $($file.Length) bytes)" -ForegroundColor White

Write-Host "8. Consider removing standalone test files if covered by proper test suite" -ForegroundColor White    }

}

Write-Host "`nAnalysis complete!" -ForegroundColor Green
$mypyFiles = $allFiles | Where-Object { $_.Name -like "*mypy*" }
if ($mypyFiles.Count -gt 1) {
    Write-Host "`n  Multiple mypy config files found:" -ForegroundColor Yellow
    foreach ($file in $mypyFiles) {
        Write-Host "    - $($file.Name) ($($file.Length) bytes)" -ForegroundColor White
    }
}

# Calculate total size of potentially removable files
$totalRedundantSize = 0
$totalRedundantSize += ($definitelyRedundant | Measure-Object -Property Size -Sum).Sum
$totalRedundantSize += ($temporary | Measure-Object -Property Size -Sum).Sum
$totalRedundantSize += ($backups | Measure-Object -Property Size -Sum).Sum

Write-Host "`n📊 SUMMARY:" -ForegroundColor Green
Write-Host "  Definitely redundant: $($definitelyRedundant.Count) files" -ForegroundColor Red
Write-Host "  Temporary/cache: $($temporary.Count) files" -ForegroundColor Yellow
Write-Host "  Backup files: $($backups.Count) files" -ForegroundColor Magenta
Write-Host "  Potentially redundant: $($potentiallyRedundant.Count) files" -ForegroundColor Yellow
Write-Host "  Documentation files: $($documentation.Count) files" -ForegroundColor Cyan
Write-Host "  Total potential space savings: $([math]::Round($totalRedundantSize/1KB, 2)) KB" -ForegroundColor White

Write-Host "`n💡 RECOMMENDATIONS:" -ForegroundColor Green
Write-Host "  1. Review and remove definitely redundant files" -ForegroundColor White
Write-Host "  2. Clean up temporary and backup files" -ForegroundColor White
Write-Host "  3. Consolidate duplicate demo/tracker files" -ForegroundColor White
Write-Host "  4. Review documentation files for current relevance" -ForegroundColor White
Write-Host "  5. Move utility scripts to scripts/ directory" -ForegroundColor White