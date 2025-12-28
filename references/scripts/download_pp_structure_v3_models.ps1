<#
PowerShell script to download and extract PP-StructureV3 related inference models.
Usage: .\download_pp_structure_v3_models.ps1 [-TargetDir <path>]
#>
param(
    [string]$TargetDir = "${PSScriptRoot}\..\models\pp_structure_v3"
)

# Ensure target directory exists (Resolve-Path fails when path does not exist)
if (-not (Test-Path -Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}
$TargetDir = (Get-Item -Path $TargetDir).FullName
Set-Location -Path $TargetDir

$urls = @(
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UVDoc_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-L_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-M_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-S_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocBlockLayout_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_table_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_3cls_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_17cls_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wired_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wireless_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wired_table_cell_det_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wireless_table_cell_det_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-S_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-L_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-M_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-L_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.bak.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_rec_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_det_infer.tar",
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_rec_infer.tar",

    "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout_plus-L_infer.tar"
)

Write-Host "Downloading $($urls.Count) model packs to: $TargetDir" -ForegroundColor Green

foreach ($url in $urls) {
    $file = [IO.Path]::GetFileName($url)
    Write-Host "- $file"

    # expected extraction dir (strip .tar or .tar.gz)
    $expectedDir = $file -replace '\.tar(\.gz)?$',''
    $expectedDirPath = Join-Path -Path $TargetDir -ChildPath $expectedDir

    if (Test-Path $expectedDirPath) {
        Write-Host "  -> '$expectedDir' already exists, skipping download and extraction" -ForegroundColor Yellow
        continue
    }

    $dest = Join-Path -Path $TargetDir -ChildPath $file

    if (-not (Test-Path $dest)) {
        try {
            Write-Host "  -> downloading $file"
            Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop
        } catch {
            Write-Warning "Failed to download $url : $_"
            continue
        }
    } else {
        Write-Host "  -> archive exists: $file"
    }

    # extract if tar
    if ($file -match "\.tar$|\.tar\.gz$") {
        # attempt to get top entry in archive to check existing extraction
        try {
            $top = (& tar -tf $dest 2>$null) | Select-Object -First 1
        } catch {
            $top = $null
        }
        if ($top) {
            $topDirName = ($top -split '/')[0]
            $candidatePath = Join-Path -Path $TargetDir -ChildPath $topDirName
            if (Test-Path $candidatePath) {
                Write-Host "  -> top-level dir '$topDirName' already exists, skipping extraction" -ForegroundColor Yellow
                continue
            }
        }

        try {
            Write-Host "  -> extracting $file"
            tar -xf $dest -C $TargetDir
        } catch {
            Write-Warning "Failed to extract $dest : $_"
        }
    }
}

# manifest
$manifest = Join-Path -Path $TargetDir -ChildPath "download_manifest.txt"
$urls | Out-File -FilePath $manifest -Encoding utf8
Write-Host "Done. Manifest: $manifest" -ForegroundColor Green
