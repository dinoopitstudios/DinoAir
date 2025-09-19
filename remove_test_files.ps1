# DinoAir Test Files Removal Script
$ErrorActionPreference = "Stop"

Write-Host "Removing test files from DinoAir repository..." -ForegroundColor Cyan
$confirm = Read-Host "Are you sure you want to remove all test files? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Aborted" -ForegroundColor Red
    exit 1
}

Write-Host "Removing test files..." -ForegroundColor Yellow

# Remove main test files
Remove-Item "API_files/pytest.ini" -ErrorAction SilentlyContinue
Remove-Item "mypy_test.ini" -ErrorAction SilentlyContinue
Remove-Item "pytest.ini" -ErrorAction SilentlyContinue
Remove-Item "red_team_testing.py" -ErrorAction SilentlyContinue

# Remove test directories
Remove-Item "API_files/tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "database/tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "models/tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "tools/tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "utils/tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "tests" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "tools/pseudocode_translator/tests" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Test files removed successfully" -ForegroundColor Green
