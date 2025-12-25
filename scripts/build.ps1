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

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Install/verify dependencies
Write-Host "Ensuring dependencies are installed..." -ForegroundColor Cyan
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies!" -ForegroundColor Red
    exit 1
}

# Verify PyInstaller is available
Write-Host "Verifying PyInstaller installation..." -ForegroundColor Cyan
$pyinstallerCommand = @"
Set-Location '$projectRoot\backend\python-onnx'
& .\.venv\Scripts\Activate.ps1
& python -c "import PyInstaller; print('PyInstaller version:', PyInstaller.__version__)"
"@
Invoke-Expression $pyinstallerCommand
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller verification failed!" -ForegroundColor Red
    exit 1
}

# Activate virtual environment and run pyinstaller in the same command
Write-Host "Building backend executable..." -ForegroundColor Cyan
Set-Location $projectRoot\backend\python-onnx
if (!(Test-Path dist)) {
    New-Item -ItemType Directory -Path dist
}
& .\.venv\Scripts\python.exe -m PyInstaller --clean paddleocr_backend.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Preparing backend executable for bundling..." -ForegroundColor Yellow
# Copy backend exe to Tauri binaries directory for sidecar bundling
$backendExe = "$projectRoot\backend\python-onnx\dist\paddleocr_backend.exe"
$tauriBinariesDir = "$projectRoot\frontend\src-tauri\binaries"
if (Test-Path $backendExe) {
    # Ensure binaries directory exists
    if (!(Test-Path $tauriBinariesDir)) {
        New-Item -ItemType Directory -Path $tauriBinariesDir -Force
    }
    # Copy backend with both naming conventions
    Copy-Item $backendExe (Join-Path $tauriBinariesDir "paddleocr_backend.exe") -Force
    Copy-Item $backendExe (Join-Path $tauriBinariesDir "paddleocr_backend-x86_64-pc-windows-msvc.exe") -Force
    Write-Host "Backend executable copied to Tauri binaries directory." -ForegroundColor Green
} else {
    Write-Host "Warning: Backend executable not found at $backendExe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 4: Building Tauri application..." -ForegroundColor Yellow
Set-Location $projectRoot\frontend

# Build the Tauri application
& npx tauri build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tauri build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "The executable can be found in: frontend\src-tauri\target\release\" -ForegroundColor Cyan

# Return to project root
Set-Location $projectRoot