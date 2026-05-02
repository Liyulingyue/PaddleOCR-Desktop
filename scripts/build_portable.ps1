#Requires -Version 5.1

param(
    [string]$OutputPath = "",
    [switch]$IncludeModels
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Building PaddleOCR Desktop (Portable)..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

if ($OutputPath -eq "") {
    $OutputPath = "$projectRoot\dist\PaddleOCR-Desktop-Portable"
}

Write-Host ""
Write-Host "Step 1: Building backend with PyInstaller..." -ForegroundColor Yellow
Set-Location $projectRoot\backend\python-onnx

if (Test-Path .\.venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
}

& python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies!" -ForegroundColor Red
    exit 1
}

if (!(Test-Path dist)) {
    New-Item -ItemType Directory -Path dist | Out-Null
}

& .\.venv\Scripts\python.exe -m PyInstaller --clean paddleocr_backend.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Building frontend with cargo..." -ForegroundColor Yellow
Set-Location $projectRoot\frontend\src-tauri

& cargo build --release
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Organizing portable package..." -ForegroundColor Yellow

if (Test-Path $OutputPath) {
    Remove-Item -Path $OutputPath -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

$frontendExe = "$projectRoot\frontend\src-tauri\target\release\PaddleOCR Desktop.exe"
$backendExe = "$projectRoot\backend\python-onnx\dist\paddleocr_backend.exe"

if (Test-Path $frontendExe) {
    Copy-Item $frontendExe "$OutputPath\PaddleOCR Desktop.exe" -Force
    Write-Host "  Copied: PaddleOCR Desktop.exe" -ForegroundColor Gray
} else {
    Write-Host "Warning: Frontend exe not found at $frontendExe" -ForegroundColor Yellow
}

if (Test-Path $backendExe) {
    Copy-Item $backendExe "$OutputPath\paddleocr_backend.exe" -Force
    Write-Host "  Copied: paddleocr_backend.exe" -ForegroundColor Gray
} else {
    Write-Host "Warning: Backend exe not found at $backendExe" -ForegroundColor Yellow
}

if ($IncludeModels) {
    $modelsSourceDir = "$projectRoot\backend\python-onnx\models"
    if (Test-Path $modelsSourceDir) {
        Copy-Item $modelsSourceDir "$OutputPath\models" -Recurse -Force
        Write-Host "  Copied: models/" -ForegroundColor Gray
    } else {
        Write-Host "Warning: Models directory not found at $modelsSourceDir" -ForegroundColor Yellow
    }
}

$readmeContent = @"
PaddleOCR Desktop (Portable)
============================

Usage:
1. Run 'PaddleOCR Desktop.exe'
2. First run will prompt to download models (if not included)

Models:
- Place models in 'models' folder next to the executable
- Or set PPOCR_MODELS_DIR environment variable

"@
$readmeContent | Out-File -FilePath "$OutputPath\README.txt" -Encoding UTF8

Write-Host ""
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "Output: $OutputPath" -ForegroundColor Cyan

$totalSize = (Get-ChildItem -Path $OutputPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Size: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan

Set-Location $projectRoot
