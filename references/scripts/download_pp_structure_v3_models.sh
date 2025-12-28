#!/usr/bin/env bash
set -euo pipefail

# Download and extract PP-StructureV3 related inference models
# Usage: bash download_pp_structure_v3_models.sh [TARGET_DIR]
# Default TARGET_DIR: ./models/pp_structure_v3

TARGET_DIR=${1:-"$(pwd)/models/pp_structure_v3"}
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

URLS=(
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UVDoc_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-L_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-M_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-S_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocBlockLayout_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_table_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_3cls_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet_layout_1x_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PicoDet-S_layout_17cls_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wired_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wireless_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wired_table_cell_det_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wireless_table_cell_det_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-S_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet-L_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-M_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_pretrained_model/PP-FormulaNet_plus-M_pretrained.pdparams" # optional pretrained checkpoint
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-FormulaNet_plus-L_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.bak.tar" # backup older version

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_rec_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_det_infer.tar"
  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_mobile_rec_infer.tar"

  "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout_plus-L_infer.tar"
)

echo "Downloading ${#URLS[@]} model packs to: $TARGET_DIR"

for url in "${URLS[@]}"; do
  filename=$(basename "$url")
  echo "- Processing: $filename"

  # derive expected top-level folder name from archive name (strip .tar/.tar.gz)
  expected_dir="${filename%%.tar}"
  expected_dir="${expected_dir%%.tar.gz}"

  if [ -d "$expected_dir" ]; then
    echo "  -> target directory '$expected_dir' already exists, skipping download and extraction"
    continue
  fi

  if [ -f "$filename" ]; then
    echo "  -> archive exists: $filename"
  else
    echo "  -> downloading $filename"
    wget -q --show-progress "$url" -O "$filename" || { echo "Failed: $url"; continue; }
  fi

  # Try to extract if it's a tar
  if [[ "$filename" == *.tar || "$filename" == *.tar.gz ]]; then
    # try to find top-level dir inside tar to avoid re-extracting
    topdir=$(tar -tf "$filename" | head -n1 | cut -d'/' -f1)
    if [ -n "$topdir" ] && [ -d "$topdir" ]; then
      echo "  -> $topdir already exists inside archive target, skipping extraction"
    else
      echo "  -> extracting $filename"
      tar -xf "$filename" || echo "  -> failed to extract $filename"
    fi
  fi
done

# write manifest
MANIFEST="$TARGET_DIR/download_manifest.txt"
{ echo "Downloaded model packs:"; for url in "${URLS[@]}"; do echo "$url"; done; } > "$MANIFEST"

echo "Done. See $TARGET_DIR and $MANIFEST"
exit 0
