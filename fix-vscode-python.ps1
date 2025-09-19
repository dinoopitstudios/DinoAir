# VS Code Python Environment Fix Script
# This script helps ensure VS Code uses the correct virtual environment

Write-Host "Fixing VS Code Python Environment Configuration..." -ForegroundColor Green

$dinoAirPath = "C:\Users\DinoP\Documents\DinoAirNew\DinoAir"
Set-Location $dinoAirPath

# Check if virtual environment exists
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonPath = Resolve-Path ".\.venv\Scripts\python.exe"
    Write-Host "Found virtual environment Python at: $pythonPath" -ForegroundColor Green

    # Activate the virtual environment
    & ".\.venv\Scripts\Activate.ps1"

    Write-Host "Environment Information:" -ForegroundColor Cyan
    Write-Host "   Python Version: $(python --version)" -ForegroundColor White
    Write-Host "   Python Path: $(where.exe python | Select-Object -First 1)" -ForegroundColor White
    Write-Host "   Virtual Env: $env:VIRTUAL_ENV" -ForegroundColor White

    Write-Host ""
    Write-Host "To fix VS Code Python interpreter:" -ForegroundColor Yellow
    Write-Host "   1. Open VS Code in this directory" -ForegroundColor White
    Write-Host "   2. Press Ctrl+Shift+P" -ForegroundColor White
    Write-Host "   3. Type 'Python: Select Interpreter'" -ForegroundColor White
    Write-Host "   4. Select: .venv\Scripts\python.exe" -ForegroundColor White
    Write-Host "   OR" -ForegroundColor White
    Write-Host "   5. Open DinoAir.code-workspace file in VS Code" -ForegroundColor White

    Write-Host ""
    Write-Host "Ready to develop! Your environment is properly configured." -ForegroundColor Green

} else {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Expected location: $dinoAirPath\.venv\Scripts\python.exe" -ForegroundColor Yellow
    Write-Host "   Please run the virtual environment setup script first." -ForegroundColor Yellow
}