"""
Test script using old PP-OCRv5 Det and Rec models on test.png
"""

import cv2
import numpy as np
from pathlib import Path

# Import old classes
from app.core.pp_onnx.pp_ocrv5det_onnx import PPOCRv5DetONNX as OldDet
from app.core.pp_onnx.pp_ocrv5rec_onnx import PPOCRv5RecONNX as OldRec


def main():
    # Path to test image
    test_image_path = Path(__file__).parent / 'test.png'

    if not test_image_path.exists():
        print(f"Test image not found at {test_image_path}")
        return

    # Load image
    image = cv2.imread(str(test_image_path))
    if image is None:
        print(f"Could not load image: {test_image_path}")
        return

    print("Loaded test image")

    # Initialize old models
    try:
        old_det_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_det-ONNX' / 'inference.onnx'
        old_det = OldDet(model_path=str(old_det_path))
        old_rec_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_rec-ONNX' / 'inference.onnx'
        old_rec = OldRec(model_path=str(old_rec_path))
        print("Old models initialized successfully")
    except Exception as e:
        print(f"Error initializing models: {e}")
        return

    # Run detection
    try:
        detections = old_det.detect(image)
        print(f"Detected {len(detections)} text regions")
        print(f"Detection results shape: {detections.shape if hasattr(detections, 'shape') else 'N/A'}")
        print(f"Sample detection: {detections[0] if len(detections) > 0 else 'None'}")
    except Exception as e:
        print(f"Error in detection: {e}")
        return

    print(f"Image shape: {image.shape}")

    # For each detection, crop and recognize
    results = []
    num_to_process = min(5, len(detections))
    print(f"Processing {num_to_process} detections")
    for i in range(num_to_process):
        det = detections[i]
        print(f"Region {i}: det shape {det.shape}, det {det}")
        # det is (4, 2) array
        points = det  # [4, 2]
        x_coords = points[:, 0]
        y_coords = points[:, 1]
        x1, y1 = np.min(x_coords), np.min(y_coords)
        x2, y2 = np.max(x_coords), np.max(y_coords)

        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        # Crop the text region
        cropped = image[y1:y2, x1:x2]
        print(f"Region {i}: bbox {x1},{y1},{x2},{y2}, cropped shape {cropped.shape}")
        if cropped.size == 0:
            continue

        # Run recognition
        try:
            rec_result = old_rec.recognize(cropped)
            print(f"  Region {i} rec_result: {rec_result}, type: {type(rec_result)}")
            if isinstance(rec_result, list) and rec_result:
                text = rec_result[0][0]
                conf = rec_result[0][1]
                print(f"  Region {i} text: '{text}' (conf: {conf:.2f})")
                results.append({
                    'bbox': [x1, y1, x2, y2],
                    'text': text,
                    'confidence': conf
                })
            else:
                print(f"  Region {i} text: '' (conf: 0.00)")
        except Exception as e:
            print(f"Error in recognition for region {i}: {e}")

    # Visualize results
    vis_image = image.copy()
    for result in results:
        bbox = result['bbox']
        text = result['text']
        conf = result['confidence']

        # Draw bbox
        cv2.rectangle(vis_image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

        # Draw text
        label = f"{text} ({conf:.2f})"
        cv2.putText(vis_image, label, (bbox[0], bbox[1] - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # Save visualization
    output_path = Path(__file__).parent / 'old_pipeline_output.png'
    cv2.imwrite(str(output_path), vis_image)
    print(f"Visualization saved to {output_path}")

    # Show image (if running interactively)
    cv2.imshow("Old Pipeline OCR Results", vis_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()