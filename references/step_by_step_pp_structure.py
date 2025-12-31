#!/usr/bin/env python3
"""
PP-Structure-V3 ONNX Step-by-Step Inference Script
Allows running and visualizing each step of the document parsing pipeline.
"""

import sys
import os
import argparse
import cv2
import numpy as np
from pathlib import Path

# Check if virtual environment is activated
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Warning: Virtual environment not activated. Please run:")
    print("source .venv/bin/activate")
    print("Then run this script again.")
    sys.exit(1)

# Add AppDemo to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AppDemo'))

from AppDemo.pipeline import PPStructureONNXPipeline

def visualize_layout_detection(image_path, regions, output_path=None, show_scores=True, save_crops=False, crops_dir=None):
    """Visualize layout detection results by drawing bounding boxes and optional debug crops"""
    image = cv2.imread(image_path)

    # Define colors for different region types
    colors = {
        'text': (0, 255, 0),      # Green
        'table': (255, 0, 0),     # Blue
        'figure': (0, 0, 255),    # Red
        'formula': (255, 255, 0), # Cyan
        'title': (255, 0, 255),   # Magenta
    }

    if save_crops and crops_dir:
        os.makedirs(crops_dir, exist_ok=True)

    for i, region in enumerate(regions):
        bbox = region['bbox']
        region_type = region['type']
        conf = region.get('confidence', None)

        # Draw rectangle
        color = colors.get(region_type, (128, 128, 128))  # Gray for unknown types
        cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

        # Add label (with confidence)
        if show_scores and conf is not None:
            label = f"{region_type} {conf:.2f}"
        else:
            label = f"{region_type}"
        cv2.putText(image, label, (bbox[0], bbox[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Save crop for debugging
        if save_crops and crops_dir:
            x1, y1, x2, y2 = bbox
            # Guard against inverted/zero boxes
            if x2 <= x1 or y2 <= y1:
                print(f"Skipping empty/invalid crop for region {i+1}: bbox={bbox}")
            else:
                crop = image[y1:y2, x1:x2]
                crop_path = os.path.join(crops_dir, f"region_{i+1}_{region_type}_{int(conf*100) if conf else 0}.png")
                try:
                    if crop.size == 0:
                        print(f"Skipping empty crop for region {i+1}: bbox={bbox}")
                    else:
                        cv2.imwrite(crop_path, crop)
                except Exception as e:
                    print(f"Failed to save crop {crop_path}: {e}")

    if output_path:
        cv2.imwrite(output_path, image)
        print(f"Visualization saved to {output_path}")
    else:
        # Display image (requires GUI support)
        cv2.imshow('Layout Detection Results', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def step_1_layout_detection(pipeline, image_path, min_conf=0.5, nms_iou=0.5, debug=False, shrink=1.0, map_mode='auto'):
    """Execute Step 1: Layout Detection with debug options"""
    print("=== Step 1: Layout Detection ===")
    print(f"Processing image: {image_path}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image {image_path}")
        return None

    print(f"Image loaded: {image.shape}")

    # Run layout detection with provided thresholds
    res = pipeline.run_layout_detection(image, min_conf, nms_iou, debug, shrink, map_mode)
    if debug and isinstance(res, tuple):
        # now res contains (regions, raw_outputs, scale, offset)
        regions, raw_outputs, scale, offset = res
        # Save raw outputs for debugging
        try:
            import pickle
            with open(image_path.replace('.png', '_layout_raw_outputs.pkl'), 'wb') as f:
                pickle.dump(raw_outputs, f)
            print("Saved raw model outputs to file (pickle)")
        except Exception as e:
            print(f"Failed to save raw outputs: {e}")

        # Visualize raw outputs on canvas for comparison and mapped visualizations using same scale/offset
        try:
            from AppDemo import utils as app_utils
            raw_vis = app_utils.visualize_raw_layout_outputs(image_path, raw_outputs, target_size=(640,640), scale=scale, offset=offset, output_path=image_path.replace('.png', '_layout_raw_vis.png').replace('.jpg','_layout_raw_vis.jpg'))
            if raw_vis:
                print(f"Raw outputs visualization saved to {raw_vis}")

            # Also generate three mapped visualizations on ORIGINAL image using different mapping assumptions
            vis1 = app_utils.map_and_visualize_on_original(image_path, raw_outputs, map_type='normalized', scale=scale, offset=offset, output_path=image_path.replace('.png', '_layout_mapped_norm.png'))
            vis2 = app_utils.map_and_visualize_on_original(image_path, raw_outputs, map_type='canvas', scale=scale, offset=offset, output_path=image_path.replace('.png', '_layout_mapped_canvas.png'))
            vis3 = app_utils.map_and_visualize_on_original(image_path, raw_outputs, map_type='center', scale=scale, offset=offset, output_path=image_path.replace('.png', '_layout_mapped_center.png'))

            if vis1:
                print(f"Mapped normalized visualization saved to {vis1}")
            if vis2:
                print(f"Mapped canvas visualization saved to {vis2}")
            if vis3:
                print(f"Mapped center visualization saved to {vis3}")

        except Exception as e:
            print(f"Failed to visualize raw outputs: {e}")
    else:
        regions = res

    print(f"Detected {len(regions)} regions (after min_conf={min_conf}, nms_iou={nms_iou}):")
    for i, region in enumerate(regions):
        print(f"  {i+1}. Type: {region['type']}, BBox: {region['bbox']}, Conf: {region.get('confidence')}")

    # Save regions to file for step 2
    import json
    regions_file = image_path.replace('.png', '_regions.json').replace('.jpg', '_regions.json')
    with open(regions_file, 'w', encoding='utf-8') as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)
    print(f"Regions saved to {regions_file}")

    # Visualize results (show scores and optionally save crops)
    vis_output = image_path.replace('.png', '_layout_vis.png').replace('.jpg', '_layout_vis.jpg')
    crops_dir = None
    if debug:
        crops_dir = image_path.replace('.png', '_layout_crops').replace('.jpg', '_layout_crops')
    visualize_layout_detection(image_path, regions, vis_output, show_scores=True, save_crops=debug, crops_dir=crops_dir)

    # Save debug regions array if debug
    if debug:
        try:
            import pickle
            with open(image_path.replace('.png', '_regions_debug.pkl'), 'wb') as f:
                pickle.dump(regions, f)
            print("Saved debug regions array (pickle)")
        except Exception as e:
            print(f"Failed to save raw outputs: {e}")

    return regions

def step_2_ocr_and_table_recognition(pipeline, image_path, regions):
    """Execute Step 2: OCR and Table Recognition"""
    print("\n=== Step 2: OCR and Table Recognition ===")

    image = cv2.imread(image_path)

    # Process text regions with OCR
    text_results = pipeline.run_ocr(image, regions)

    # Process table regions
    table_results = []
    for region in regions:
        if region['type'] == 'table':
            # Here you would add table recognition logic
            # For now, just mark as processed
            table_results.append({
                'bbox': region['bbox'],
                'type': 'table',
                'content': 'Table content (placeholder)'
            })

    print(f"OCR processed {len(text_results)} text regions")
    print(f"Table recognition processed {len(table_results)} table regions")

    return text_results, table_results

def main():
    parser = argparse.ArgumentParser(description='PP-Structure-V3 ONNX Step-by-Step Inference')
    parser.add_argument('input_image', nargs='?', default='test_document.png',
                       help='Path to input image file (default: test_document.png)')
    parser.add_argument('--step', '-s', type=int, choices=[1, 2], default=1,
                       help='Step to execute (1: Layout Detection, 2: OCR and Tables)')
    parser.add_argument('--min-conf', type=float, default=0.5, help='Minimum confidence for detections (default 0.5)')
    parser.add_argument('--nms-iou', type=float, default=0.5, help='NMS IoU threshold (default 0.5)')
    parser.add_argument('--shrink', type=float, default=1.0, help='Shrink factor for bboxes (0.0-1.0, default 1.0 means no shrink)')
    parser.add_argument('--map-mode', choices=['auto','canvas','normalized','center'], default='auto', help='Force mapping mode for model outputs when mapping back to original coords (default auto)')
    parser.add_argument('--max-box-ratio', type=float, default=0.9, help='Maximum box width/height as ratio of image size (default 0.9)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode: show scores and save crop images')

    args = parser.parse_args()

    if not os.path.exists(args.input_image):
        print(f"Error: Input image '{args.input_image}' not found")
        return 1

    # Initialize pipeline
    pipeline = PPStructureONNXPipeline()

    if args.step == 1:
        # Execute Step 1 with provided options
        regions = step_1_layout_detection(pipeline, args.input_image, min_conf=args.min_conf, nms_iou=args.nms_iou, debug=args.debug, shrink=args.shrink, map_mode=args.map_mode, max_box_ratio=args.max_box_ratio)

        if regions is None:
            return 1

        print("\nStep 1 completed successfully!")
        print("Check the visualization files (raw/mapped) to confirm the layout detection results.")
        print("When ready, run this script again with --step 2 to continue.")

    elif args.step == 2:
        # Load regions from step 1
        import json
        regions_file = args.input_image.replace('.png', '_regions.json').replace('.jpg', '_regions.json')
        if not os.path.exists(regions_file):
            print(f"Error: Regions file {regions_file} not found.")
            print("Please run Step 1 first.")
            return 1

        with open(regions_file, 'r', encoding='utf-8') as f:
            regions = json.load(f)

        print(f"Loaded {len(regions)} regions from {regions_file}")

        # Execute Step 2
        text_results, table_results = step_2_ocr_and_table_recognition(pipeline, args.input_image, regions)

        print("\nStep 2 completed successfully!")
        print("All steps completed. You can now run the full pipeline if desired.")

    return 0

if __name__ == '__main__':
    sys.exit(main())