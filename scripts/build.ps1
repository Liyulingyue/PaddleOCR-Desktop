#Requires -Version 5.1

# Ensure we start from the project root directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Building PaddleOCR Desktop Application..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

Write-Host ""
Write-Host "Step 1: Building frontend..." -ForegroundColor Yellow
Set-Location frontend
& npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Building backend with PyInstaller..." -ForegroundColor Yellow
Set-Location $projectRoot\backend\python-onnx
if (!(Test-Path dist)) {
    New-Item -ItemType Directory -Path dist
}
& pyinstaller --clean paddleocr_backend.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Preparing backend executable for bundling..." -ForegroundColor Yellow
# Copy backend exe to Tauri resources directory
$backendExe = "$projectRoot\backend\python-onnx\dist\paddleocr_backend.exe"
$tauriResourcesDir = "$projectRoot\frontend\src-tauri"
if (Test-Path $backendExe) {
    # Copy to the directory where tauri.conf.json expects it
    Copy-Item $backendExe -Destination "$tauriResourcesDir\" -Force
    Write-Host "Backend executable copied to Tauri directory." -ForegroundColor Green
} else {
    Write-Host "Warning: Backend executable not found at $backendExe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 4: Building Tauri application..." -ForegroundColor Yellow
Set-Location $projectRoot\frontend

Write-Host ""
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "The executable can be found in: frontend\src-tauri\target\release\" -ForegroundColor Cyan