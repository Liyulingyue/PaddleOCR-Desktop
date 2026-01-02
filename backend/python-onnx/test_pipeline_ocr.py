"""
Simple OCR Pipeline combining Det and Rec models
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict

from app.core.pp_onnx.pp_ocrv5det_onnx import PPOCRv5DetONNX
from app.core.pp_onnx.pp_ocrv5rec_onnx import PPOCRv5RecONNX


class SimpleOCRPipeline:
    def __init__(self, det_model_path: str, rec_model_path: str):
        self.det_model = PPOCRv5DetONNX(model_path=det_model_path)
        self.rec_model = PPOCRv5RecONNX(model_path=rec_model_path)

    def ocr(self, image: np.ndarray, det_conf_threshold: float = 0.3) -> List[Dict]:
        """
        Run full OCR pipeline: detection + recognition

        Args:
            image: Input image
            det_conf_threshold: Detection confidence threshold

        Returns:
            List of OCR results with bbox, text, confidence
        """
        # Run detection
        detections = self.det_model.detect(image)

        results = []
        for det in detections:
            # det is numpy array of shape (4, 2) for quad points
            points = det  # [4, 2]
            x_coords = points[:, 0]
            y_coords = points[:, 1]
            x1, y1 = int(np.min(x_coords)), int(np.min(y_coords))
            x2, y2 = int(np.max(x_coords)), int(np.max(y_coords))

            # Crop text region
            cropped = image[y1:y2, x1:x2]
            if cropped.size == 0:
                continue

            # Run recognition
            try:
                rec_result = self.rec_model.recognize(cropped)
                if isinstance(rec_result, list) and rec_result:
                    text = rec_result[0][0]
                    conf = rec_result[0][1]
                else:
                    text = ''
                    conf = 0.0
            except:
                text = ''
                conf = 0.0

            results.append({
                'bbox': [x1, y1, x2, y2],
                'text': text,
                'confidence': conf
            })

        return results


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

    # Initialize pipeline
    try:
        det_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_det-ONNX' / 'inference.onnx'
        rec_path = Path(__file__).parent / 'models' / 'PP-OCRv5_mobile_rec-ONNX' / 'inference.onnx'
        pipeline = SimpleOCRPipeline(str(det_path), str(rec_path))
        print("Pipeline initialized")
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        return

    # Run OCR
    try:
        ocr_results = pipeline.ocr(image)
        print(f"OCR completed: {len(ocr_results)} results")
        for i, result in enumerate(ocr_results[:10]):  # Show first 10
            print(f"  {i}: {result}")
    except Exception as e:
        print(f"Error in OCR: {e}")
        return

    # Visualize
    vis_image = image.copy()
    for result in ocr_results:
        bbox = result['bbox']
        text = result['text']
        conf = result['confidence']

        cv2.rectangle(vis_image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
        label = f"{text} ({conf:.2f})"
        cv2.putText(vis_image, label, (bbox[0], bbox[1] - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    output_path = Path(__file__).parent / 'pipeline_ocr_output.png'
    cv2.imwrite(str(output_path), vis_image)
    print(f"Visualization saved to {output_path}")


if __name__ == "__main__":
    main()