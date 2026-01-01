#!/bin/bash

# Batch convert all models in models_pp to ONNX format
# Places converted models in models_onnx directory

OUTPUT_BASE="models_onnx"
mkdir -p "$OUTPUT_BASE"

for model_dir in models_pp/*/; do
    if [ -d "$model_dir" ]; then
        model_name=$(basename "$model_dir")
        output_dir="$OUTPUT_BASE/$model_name"
        echo "Converting $model_name..."
        if ./convert_to_onnx.sh "$model_dir" "$output_dir"; then
            echo "$model_name converted successfully"
        else
            echo "Failed to convert $model_name"
        fi
    fi
done

echo "Batch conversion complete."