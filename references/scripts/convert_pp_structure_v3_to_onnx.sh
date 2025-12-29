#!/bin/bash

# Script to batch convert PP-StructureV3 models to ONNX format
# Creates pp_structure_v3_onnx/ folder and saves converted models there
# Assumes models are downloaded in models/ directory
# Requires paddle2onnx to be installed

# Activate virtual environment
source ../.venv/bin/activate

set -e

# Create output directory
OUTPUT_DIR="pp_structure_v3_onnx"
mkdir -p "$OUTPUT_DIR"

# CSV log file
LOG_FILE="paddle2onnx_conversion_results.csv"
echo "Model,Status,Error" > "$LOG_FILE"

# Function to convert a model
convert_model() {
    local model_name="$1"
    local model_dir="$2"
    local output_file="$OUTPUT_DIR/${model_name}.onnx"

    if [ ! -d "$model_dir" ]; then
        echo "$model_name,Failed,Model directory not found: $model_dir" >> "$LOG_FILE"
        return 1
    fi

    echo "Converting $model_name..."

    if python -m paddle2onnx \
        --model_dir "$model_dir" \
        --model_filename "inference.pdmodel" \
        --params_filename "inference.pdiparams" \
        --save_file "$output_file" \
        --opset_version 11 \
        --enable_onnx_checker True; then
        echo "$model_name,Success," >> "$LOG_FILE"
        echo "Converted $model_name successfully"
    else
        echo "$model_name,Failed,Conversion command failed" >> "$LOG_FILE"
        echo "Failed to convert $model_name"
    fi
}

# Model list from compatibility table
# Note: Adjust paths based on actual download locations
convert_model "PP-LCNet_x1_0_doc_ori" "models/ppocrv5/PP-LCNet_x1_0_doc_ori_infer"
convert_model "UVDoc" "models/ppocrv5/UVDoc_infer"
convert_model "PP-DocLayout-L" "models/ppocrv5/PP-DocLayout-L_infer"
convert_model "PP-DocLayout-M" "models/ppocrv5/PP-DocLayout-M_infer"
convert_model "PP-DocLayout-S" "models/ppocrv5/PP-DocLayout-S_infer"
convert_model "PicoDet_layout_1x_table" "models/ppocrv5/PicoDet_layout_1x_table_infer"
convert_model "PicoDet-S_layout_3cls" "models/ppocrv5/PicoDet-S_layout_3cls_infer"
convert_model "PicoDet-S_layout_17cls" "models/ppocrv5/PicoDet-S_layout_17cls_infer"
convert_model "PicoDet_layout_1x" "models/ppocrv5/PicoDet_layout_1x_infer"
convert_model "PP-OCRv5_det" "models/ppocrv5/PP-OCRv5_server_det_infer"
convert_model "PP-OCRv5_rec" "models/ppocrv5/PP-OCRv5_server_rec_infer"
convert_model "PP-OCRv5_cls" "models/ppocrv5/PP-OCRv5_server_cls_infer"
convert_model "RT-DETR-L_wired_table_cell_det" "models/ppocrv5/RT-DETR-L_wired_table_cell_det_infer"
convert_model "RT-DETR-L_wireless_table_cell_det" "models/ppocrv5/RT-DETR-L_wireless_table_cell_det_infer"
convert_model "SLANeXt_wired" "models/ppocrv5/SLANeXt_wired_infer"
convert_model "SLANeXt_wireless" "models/ppocrv5/SLANeXt_wireless_infer"
convert_model "PP-FormulaNet-S" "models/ppocrv5/PP-FormulaNet-S_infer"
convert_model "PP-FormulaNet-L" "models/ppocrv5/PP-FormulaNet-L_infer"
convert_model "PP-FormulaNet_plus-M" "models/ppocrv5/PP-FormulaNet_plus-M_infer"
convert_model "PP-FormulaNet_plus-L" "models/ppocrv5/PP-FormulaNet_plus-L_infer"
convert_model "PP-Chart2Table" "models/ppocrv5/PP-Chart2Table_infer"

echo "Conversion complete. Check $LOG_FILE for results."