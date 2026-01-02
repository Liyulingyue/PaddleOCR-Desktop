"""
Compare old and new PP-OCRv5 Det and Rec models on test.png
"""

import cv2
import numpy as np
from pathlib import Path

# Import new classes
from app.core.pp_onnx.pp_ocrv5det_onnx_new import PPOCRv5DetONNX as NewDet
from app.core.pp_onnx.pp_ocrv5rec_onnx_new import PPOCRv5RecONNX as NewRec

# Import old classes
from app.core.pp_onnx.pp_ocrv5det_onnx import PPOCRv5DetONNX as OldDet
from app.core.pp_onnx.pp_ocrv5rec_onnx import PPOCRv5RecONNX as OldRec


def compare_detections(old_results, new_results):
    print(f"Old detections: {len(old_results) if hasattr(old_results, '__len__') else 'N/A'}")
    print(f"New detections: {len(new_results)}")
    print(f"Old results type: {type(old_results)}")
    print(f"New results type: {type(new_results)}")
    # For now, just print counts and types


def compare_recognitions(old_results, new_results):
    print(f"Old recognitions: {len(old_results)}")
    print(f"New recognitions: {len(new_results)}")

    for i, (old, new) in enumerate(zip(old_results, new_results)):
        old_text = old.get('text', '')
        new_text = new.get('text', '')
        print(f"Region {i}: Old: '{old_text}' | New: '{new_text}'")


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

    # Initialize models
    try:
        old_det_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_det-ONNX' / 'inference.onnx'
        old_det = OldDet(model_path=str(old_det_path))
        new_det = NewDet()
        old_rec_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_rec-ONNX' / 'inference.onnx'
        old_rec = OldRec(model_path=str(old_rec_path))
        new_rec = NewRec()
        print("Models initialized")
    except Exception as e:
        print(f"Error initializing models: {e}")
        return

    # Run old detection
    try:
        old_detections = old_det.detect(image)
        print("Old detection completed")
    except Exception as e:
        print(f"Error in old detection: {e}")
        old_detections = []

    # Run new detection
    try:
        new_detections = new_det.detect(image, conf_threshold=0.3)
        print("New detection completed")
    except Exception as e:
        print(f"Error in new detection: {e}")
        new_detections = []

    # Compare detections
    compare_detections(old_detections, new_detections)

    # Use new detections for recognition comparison
    detections = new_detections

    # For each detection, crop and recognize with old rec
    old_rec_results = []
    for det in detections[:5]:  # Limit to first 5 for speed
        bbox = det['bbox']
        x1, y1, x2, y2 = bbox
        cropped = image[y1:y2, x1:x2]
        if cropped.size == 0:
            continue
        try:
            result = old_rec.recognize(cropped)
            if isinstance(result, list) and result:
                old_rec_results.append({'text': result[0][0], 'confidence': result[0][1]})
            else:
                old_rec_results.append({'text': '', 'confidence': 0.0})
        except Exception as e:
            print(f"Error in old recognition: {e}")
            old_rec_results.append({'text': '', 'confidence': 0.0})

    # For each detection, crop and recognize with new rec
    new_rec_results = []
    for det in detections[:5]:  # Limit to first 5
        bbox = det['bbox']
        x1, y1, x2, y2 = bbox
        cropped = image[y1:y2, x1:x2]
        if cropped.size == 0:
            continue
        try:
            result = new_rec.recognize(cropped)
            new_rec_results.append(result)
        except Exception as e:
            print(f"Error in new recognition: {e}")
            new_rec_results.append({'text': '', 'confidence': 0.0})

    # Compare recognitions
    compare_recognitions(old_rec_results, new_rec_results)


if __name__ == "__main__":
    main()