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