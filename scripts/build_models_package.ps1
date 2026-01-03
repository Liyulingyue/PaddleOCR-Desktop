#Requires -Version 5.1

# 构建模型资源包脚本
# 将模型文件打包为独立的zip包，方便分发

param(
    [string]$OutputPath = "",
    [switch]$IncludeAllModels
)

# 确保从项目根目录开始
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Building PaddleOCR Models Package..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

# 设置输出路径
if ($OutputPath -eq "") {
    $OutputPath = "$projectRoot\dist\models-package.zip"
}

# 模型源目录
$modelsSourceDir = "$projectRoot\backend\python-onnx\models"

# 检查模型目录是否存在
if (!(Test-Path $modelsSourceDir)) {
    Write-Host "Error: Models directory not found at $modelsSourceDir" -ForegroundColor Red
    exit 1
}

Write-Host "Models source directory: $modelsSourceDir" -ForegroundColor Cyan

# 创建临时目录用于打包
$tempDir = "$env:TEMP\PaddleOCR-Models-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host "Copying models to temporary directory..." -ForegroundColor Yellow

    # 复制所有模型文件
    $modelsDirs = Get-ChildItem -Path $modelsSourceDir -Directory
    foreach ($dir in $modelsDirs) {
        $destDir = Join-Path $tempDir $dir.Name
        Write-Host "  Copying $($dir.Name)..." -ForegroundColor Gray
        Copy-Item -Path $dir.FullName -Destination $destDir -Recurse -Force
    }

    # 创建包信息文件
    $packageInfo = @"
PaddleOCR Desktop Models Package
================================

This package contains all the machine learning models required for PaddleOCR Desktop.

Installation:
1. Extract this zip file to a directory of your choice
2. Set the PPOCR_MODELS_DIR environment variable to point to this directory
   Example: set PPOCR_MODELS_DIR=C:\path\to\extracted\models
3. Or place the 'models' folder in the same directory as the PaddleOCR Desktop executable

Included Models:
$(Get-ChildItem -Path $tempDir -Directory | ForEach-Object { "  - $($_.Name)" } | Out-String)

Package created on: $(Get-Date)
"@

    $packageInfo | Out-File -FilePath (Join-Path $tempDir "README.txt") -Encoding UTF8

    Write-Host "Creating models package..." -ForegroundColor Yellow

    # 确保输出目录存在
    $outputDir = Split-Path -Parent $OutputPath
    if (!(Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }

    # 创建zip包
    Compress-Archive -Path "$tempDir\*" -DestinationPath $OutputPath -Force

    # 获取包大小
    $packageSize = (Get-Item $OutputPath).Length / 1MB

    Write-Host "Models package created successfully!" -ForegroundColor Green
    Write-Host "Output: $OutputPath" -ForegroundColor Cyan
    Write-Host "Size: $([math]::Round($packageSize, 2)) MB" -ForegroundColor Cyan

    # 显示包含的模型
    Write-Host "Included models:" -ForegroundColor Yellow
    Get-ChildItem -Path $tempDir -Directory | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Gray
    }

} finally {
    # 清理临时目录
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force
    }
}

Write-Host ""
Write-Host "To use this package:" -ForegroundColor Yellow
Write-Host "1. Extract the zip file to your preferred location" -ForegroundColor White
Write-Host "2. Set PPOCR_MODELS_DIR environment variable, or" -ForegroundColor White
Write-Host "3. Place the 'models' folder next to the executable" -ForegroundColor White
Write-Host ""
Write-Host "Package build completed!" -ForegroundColor Green