#!/bin/bash

# Script to convert a single PP-StructureV3 model to ONNX format
# Usage: ./convert_to_onnx.sh <model_dir> <output_dir>
# Automatically sets up virtual environment and installs required packages

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <model_dir> <output_dir>"
    exit 1
fi

MODEL_DIR="$1"
OUTPUT_DIR="$2"

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements if not already installed
if [ ! -f ".venv/requirements_installed" ]; then
    echo "Installing requirements..."
    pip install --upgrade pip
    pip install paddlex
    pip install paddlepaddle
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    paddlex --install paddle2onnx
    touch .venv/requirements_installed
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if model directory exists
if [ ! -d "$MODEL_DIR" ]; then
    echo "Error: Model directory not found: $MODEL_DIR"
    exit 1
fi

# If common paddle model files are not directly in MODEL_DIR, check for a single nested subdir
if [ ! -f "$MODEL_DIR/inference.pdiparams" ] && [ ! -f "$MODEL_DIR/model_state.pdparams" ]; then
    # gather immediate subdirectories
    mapfile -t subdirs < <(find "$MODEL_DIR" -maxdepth 1 -mindepth 1 -type d -printf "%p\n")
    if [ ${#subdirs[@]} -eq 1 ]; then
        candidate="${subdirs[0]}"
        if [ -f "$candidate/inference.pdiparams" ] || [ -f "$candidate/model_state.pdparams" ]; then
            echo "Using nested model directory: $candidate"
            MODEL_DIR="$candidate"
        fi
    fi
fi

echo "Converting model from $MODEL_DIR to $OUTPUT_DIR..."

# Use paddlex for conversion
if paddlex \
    --paddle2onnx \
    --paddle_model_dir "$MODEL_DIR" \
    --onnx_model_dir "$OUTPUT_DIR" \
    --opset_version 7; then
    echo "Conversion successful"
else
    echo "Conversion failed"
    exit 1
fi