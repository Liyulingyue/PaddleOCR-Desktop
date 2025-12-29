#!/bin/bash

# Script to batch convert PP-StructureV3 models to ONNX format
# Creates pp_structure_v3_onnx/ folder and saves converted models there
# Assumes models are downloaded in models/ directory
# Requires paddle2onnx to be installed

# Activate virtual environment
source .venv/bin/activate

# set -e  # Removed to allow script to continue on conversion failures

# Create output directory
OUTPUT_DIR="models/pp_structure_v3_onnx"
mkdir -p "$OUTPUT_DIR"

# CSV log file
LOG_FILE="paddle2onnx_conversion_results.csv"
echo "Model,Status,Error" > "$LOG_FILE"

# Function to convert a model
convert_model() {
    local model_name="$1"
    local model_dir="$2"
    local model_output_dir="$OUTPUT_DIR/$model_name"

    if [ -d "$model_output_dir" ] && [ -n "$(ls -A "$model_output_dir" 2>/dev/null)" ]; then
        echo "$model_name,Skipped,Already converted" >> "$LOG_FILE"
        echo "Skipped $model_name (already converted)"
        return 0
    fi

    mkdir -p "$model_output_dir"

    if [ ! -d "$model_dir" ]; then
        echo "$model_name,Failed,Model directory not found: $model_dir" >> "$LOG_FILE"
        return 1
    fi

    echo "Converting $model_name..."

    if paddlex \
        --paddle2onnx \
        --paddle_model_dir "$model_dir" \
        --onnx_model_dir "$model_output_dir" \
        --opset_version 7; then
        echo "$model_name,Success," >> "$LOG_FILE"
        echo "Converted $model_name successfully"
    else
        echo "$model_name,Failed,Conversion command failed" >> "$LOG_FILE"
        echo "Failed to convert $model_name"
    fi
}

# Model list from compatibility table
# Note: Adjust paths based on actual download locations
convert_model "PP-LCNet_x1_0_doc_ori" "models/pp_structure_v3/PP-LCNet_x1_0_doc_ori_infer"
convert_model "UVDoc" "models/pp_structure_v3/UVDoc_infer"
convert_model "PP-DocLayout-L" "models/pp_structure_v3/PP-DocLayout-L_infer"
convert_model "PP-DocLayout-M" "models/pp_structure_v3/PP-DocLayout-M_infer"
convert_model "PP-DocLayout-S" "models/pp_structure_v3/PP-DocLayout-S_infer"
convert_model "PicoDet_layout_1x_table" "models/pp_structure_v3/PicoDet_layout_1x_table_infer"
convert_model "PicoDet-S_layout_3cls" "models/pp_structure_v3/PicoDet-S_layout_3cls_infer"
convert_model "PicoDet-S_layout_17cls" "models/pp_structure_v3/PicoDet-S_layout_17cls_infer"
convert_model "PicoDet_layout_1x" "models/pp_structure_v3/PicoDet_layout_1x_infer"
convert_model "PP-OCRv5_det" "models/pp_structure_v3/PP-OCRv5_server_det_infer"
convert_model "PP-OCRv5_rec" "models/pp_structure_v3/PP-OCRv5_server_rec_infer"
convert_model "RT-DETR-L_wired_table_cell_det" "models/pp_structure_v3/RT-DETR-L_wired_table_cell_det_infer"
convert_model "RT-DETR-L_wireless_table_cell_det" "models/pp_structure_v3/RT-DETR-L_wireless_table_cell_det_infer"
convert_model "SLANeXt_wired" "models/pp_structure_v3/SLANeXt_wired_infer"
convert_model "SLANeXt_wireless" "models/pp_structure_v3/SLANeXt_wireless_infer"
convert_model "PP-FormulaNet-S" "models/pp_structure_v3/PP-FormulaNet-S_infer"
convert_model "PP-FormulaNet-L" "models/pp_structure_v3/PP-FormulaNet-L_infer"
convert_model "PP-FormulaNet_plus-M" "models/pp_structure_v3/PP-FormulaNet_plus-M_infer"
convert_model "PP-FormulaNet_plus-L" "models/pp_structure_v3/PP-FormulaNet_plus-L_infer"
convert_model "PP-Chart2Table" "models/pp_structure_v3/PP-Chart2Table"
convert_model "PP-DocBlockLayout" "models/pp_structure_v3/PP-DocBlockLayout_infer"
convert_model "PP-DocLayout_plus-L" "models/pp_structure_v3/PP-DocLayout_plus-L_infer"
convert_model "PP-OCRv5_mobile_det" "models/pp_structure_v3/PP-OCRv5_mobile_det_infer"
convert_model "PP-OCRv5_mobile_rec" "models/pp_structure_v3/PP-OCRv5_mobile_rec_infer"

echo "Conversion complete. Check $LOG_FILE for results."