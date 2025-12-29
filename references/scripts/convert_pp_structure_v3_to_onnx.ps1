# Script to batch convert PP-StructureV3 models to ONNX format
# Creates pp_structure_v3_onnx/ folder and saves converted models there
# Assumes models are downloaded in models/ directory
# Requires paddle2onnx to be installed (via pip install paddle2onnx)

param()

# Path to paddle2onnx executable
$Paddle2OnnxExe = "paddle2onnx"

# Activation is required for paddle2onnx to be in PATH
$activatePath = $null
$venvCandidates = @(
    ".\.venv\Scripts\Activate.ps1",
    "venv\Scripts\Activate.ps1",
    "..\.venv\Scripts\Activate.ps1",
    "..\venv\Scripts\Activate.ps1"
)
# If running inside an activated venv, prefer that
if ($env:VIRTUAL_ENV) {
    $candidate = Join-Path $env:VIRTUAL_ENV "Scripts\Activate.ps1"
    $venvCandidates = ,$candidate + $venvCandidates
}
foreach ($p in $venvCandidates) {
    if (Test-Path $p) {
        $activatePath = (Resolve-Path $p).Path
        break
    }
}
if ($activatePath) {
    & $activatePath
}
else {
    Write-Warning "Activate.ps1 not found in any venv candidates; paddle2onnx may not be available"
}

# Create output directory
$OutputDir = "models/pp_structure_v3_onnx"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# CSV log file
$LogFile = "paddle2onnx_conversion_results.csv"
"Model,Status,Error" | Out-File -FilePath $LogFile -Encoding UTF8

# Function to convert a model
function Convert-Model {
    param(
        [string]$ModelName,
        [string]$ModelDir,
        [string]$OutputFile = "$OutputDir\$ModelName.onnx"
    )

    if (!(Test-Path $ModelDir)) {
        "$ModelName,Failed,Model directory not found: $ModelDir" | Out-File -FilePath $LogFile -Append -Encoding UTF8
        return
    }

    Write-Host "Converting $ModelName..."

    try {
        & $Paddle2OnnxExe `
            --model_dir $ModelDir `
            --model_filename "inference.pdmodel" `
            --params_filename "inference.pdiparams" `
            --save_file $OutputFile `
            --opset_version 11 `
            --enable_onnx_checker True

        "$ModelName,Success," | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host "Converted $ModelName successfully"
    }
    catch {
        "$ModelName,Failed,$($_.Exception.Message)" | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host "Failed to convert $ModelName"
    }
}

# Model list from compatibility table
# Note: Adjust paths based on actual download locations
Convert-Model "PP-LCNet_x1_0_doc_ori" "models\pp_structure_v3\PP-LCNet_x1_0_doc_ori_infer"
Convert-Model "UVDoc" "models\pp_structure_v3\UVDoc_infer"
Convert-Model "PP-DocLayout-L" "models\pp_structure_v3\PP-DocLayout-L_infer"
Convert-Model "PP-DocLayout-M" "models\pp_structure_v3\PP-DocLayout-M_infer"
Convert-Model "PP-DocLayout-S" "models\pp_structure_v3\PP-DocLayout-S_infer"
Convert-Model "PicoDet_layout_1x_table" "models\pp_structure_v3\PicoDet_layout_1x_table_infer"
Convert-Model "PicoDet-S_layout_3cls" "models\pp_structure_v3\PicoDet-S_layout_3cls_infer"
Convert-Model "PicoDet-S_layout_17cls" "models\pp_structure_v3\PicoDet-S_layout_17cls_infer"
Convert-Model "PicoDet_layout_1x" "models\pp_structure_v3\PicoDet_layout_1x_infer"
Convert-Model "PP-OCRv5_det" "models\pp_structure_v3\PP-OCRv5_server_det_infer"
Convert-Model "PP-OCRv5_rec" "models\pp_structure_v3\PP-OCRv5_server_rec_infer"
Convert-Model "PP-OCRv5_cls" "models\pp_structure_v3\PP-OCRv5_server_cls_infer"
Convert-Model "RT-DETR-L_wired_table_cell_det" "models\pp_structure_v3\RT-DETR-L_wired_table_cell_det_infer"
Convert-Model "RT-DETR-L_wireless_table_cell_det" "models\pp_structure_v3\RT-DETR-L_wireless_table_cell_det_infer"
Convert-Model "SLANeXt_wired" "models\pp_structure_v3\SLANeXt_wired_infer"
Convert-Model "SLANeXt_wireless" "models\pp_structure_v3\SLANeXt_wireless_infer"
Convert-Model "PP-FormulaNet-S" "models\pp_structure_v3\PP-FormulaNet-S_infer"
Convert-Model "PP-FormulaNet-L" "models\pp_structure_v3\PP-FormulaNet-L_infer"
Convert-Model "PP-FormulaNet_plus-M" "models\pp_structure_v3\PP-FormulaNet_plus-M_infer"
Convert-Model "PP-FormulaNet_plus-L" "models\pp_structure_v3\PP-FormulaNet_plus-L_infer"
Convert-Model "PP-Chart2Table" "models\pp_structure_v3\PP-Chart2Table_infer"

Write-Host "Conversion complete. Check $LogFile for results."