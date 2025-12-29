#!/usr/bin/env python3
"""
PP-Structure-V3 ONNX Inference Entry Point
Runs the complete document parsing pipeline using ONNX models.
"""

import sys
import os
import argparse
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

def main():
    parser = argparse.ArgumentParser(description='PP-Structure-V3 ONNX Inference')
    parser.add_argument('input_image', nargs='?', default='test_document.png', 
                       help='Path to input image file (default: test_document.png)')
    parser.add_argument('--output', '-o', default='result', 
                       help='Output file base name (default: result, will create result.json and result.md)')

    args = parser.parse_args()

    if not os.path.exists(args.input_image):
        print(f"Error: Input image '{args.input_image}' not found")
        return 1

    # Initialize pipeline
    pipeline = PPStructureONNXPipeline()

    # Run inference
    try:
        result = pipeline.run(args.input_image)

        # Save JSON result
        import json
        json_output = args.output + '.json'
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"JSON result saved to {json_output}")

        # Save Markdown result
        markdown = pipeline.result_to_markdown(result)
        md_output = args.output + '.md'
        with open(md_output, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"Markdown result saved to {md_output}")

    except Exception as e:
        print(f"Error during inference: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())