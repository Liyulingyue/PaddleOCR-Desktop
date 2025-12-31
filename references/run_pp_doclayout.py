#!/home/liyulingyue/Codes/PaddleOCR-Desktop/references/.venv/bin/python3
"""
Example script to run PP-DocLayout ONNX inference
"""

import cv2
import sys
import os
from AppDemo.pp_doclayout_onnx import PPDocLayoutONNX

def run_pp_doclayout_example(image_path: str, output_path: str = None):
    """
    Run PP-DocLayout detection on an image

    Args:
        image_path: Path to input image
        output_path: Path to save visualization (optional)
    """
    print(f"Loading image: {image_path}")

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return

    print(f"Image loaded: {image.shape}")

    try:
        # Initialize PP-DocLayout detector
        print("Initializing PP-DocLayout detector...")
        detector = PPDocLayoutONNX()

        # Display configuration info
        config = detector.get_config_info()
        print("Model Configuration: {config}")

        # Run detection
        print("Running layout detection...")
        regions = detector.detect(image, conf_threshold=0.3)

        print(f"✓ Detected {len(regions)} layout regions")

        # Print results
        print("\nDetected regions:")
        for i, region in enumerate(regions, 1):
            bbox = region['bbox']
            print(f"{i}. {region['type']} (conf: {region['confidence']:.3f}) - bbox: {bbox}")

        # Visualize and save
        if output_path:
            print(f"Saving visualization to: {output_path}")
            vis_image = detector.visualize(image, regions, output_path)
            print("✓ Visualization saved")
        else:
            print("No output path specified, displaying result...")
            vis_image = detector.visualize(image, regions)
            cv2.imshow("PP-DocLayout Detection Result", vis_image)
            print("Press any key to close the window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    except Exception as e:
        print(f"Error during detection: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python run_pp_doclayout.py <image_path> [output_visualization_path]")
        print("\nExample:")
        print("  python run_pp_doclayout.py test_document.png result.png")
        print("  python run_pp_doclayout.py test_document.png  # Display only")
        return

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    run_pp_doclayout_example(image_path, output_path)

if __name__ == "__main__":
    main()