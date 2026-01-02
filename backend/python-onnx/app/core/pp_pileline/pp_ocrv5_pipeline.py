"""
PP-OCRv5 Complete Pipeline ONNX Inference
Integrates document orientation detection, text detection, and text recognition
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import yaml

from ..pp_onnx.pp_ocrv5det_onnx import PPOCRv5DetONNX
from ..pp_onnx.pp_ocrv5rec_onnx import PPOCRv5RecONNX
from ..pp_onnx.pp_lcnet_doc_onnx import PPLCNetDocONNX


class PPOCRv5Pipeline:
    """
    Complete PP-OCRv5 Pipeline integrating orientation detection, text detection, and recognition
    """
    
    def __init__(self, 
                 det_model_path: str = None,
                 rec_model_path: str = None, 
                 cls_model_path: str = None,
                 use_gpu: bool = False, 
                 gpu_id: int = 0):
        """
        Initialize the complete PP-OCRv5 pipeline
        
        Args:
            det_model_path: Path to detection model (optional, uses default)
            rec_model_path: Path to recognition model (optional, uses default)
            cls_model_path: Path to classification model (optional, uses default)
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        # Store configuration, don't load models yet
        self.det_model_path = det_model_path
        self.rec_model_path = rec_model_path
        self.cls_model_path = cls_model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        
        # Model instances (initialized in load())
        self.cls_model = None
        self.det_model = None
        self.rec_model = None
        
        print("PP-OCRv5 Pipeline initialized (models not loaded yet). Call load() to load models.")

    def ocr(self, image: np.ndarray, conf_threshold: float = 0.5, use_close: bool = True, cls_thresh: float = 0.9, use_cls: bool = True) -> List[Dict]:
        """
        Run complete OCR pipeline on input image
        
        Args:
            image: Input image (BGR format)
            conf_threshold: Confidence threshold for detection and recognition
            use_close: Whether to use morphological closing in detection
            cls_thresh: Confidence threshold for classification
            use_cls: Whether to use document orientation classification
            
        Returns:
            List of OCR results with text, bbox, confidence
        """
        if not self.is_loaded():
            print("PP-OCRv5 models not loaded, auto-loading...")
            if not self.load():
                raise RuntimeError("Failed to auto-load PP-OCRv5 models.")
            
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")
        
        # Step 1: Document orientation detection (optional)
        angle = 0
        rotation_confidence = 1.0
        if use_cls:
            cls_result = self.cls_model.classify(image)
            if cls_result['confidence'] >= cls_thresh:
                angle = int(cls_result['angle'])
                rotation_confidence = cls_result['confidence']
            else:
                # Low confidence, assume no rotation needed
                angle = 0
                rotation_confidence = 1.0
        else:
            # Skip classification, assume no rotation
            angle = 0
            rotation_confidence = 1.0
        
        # Step 2: Rotate image based on detected angle
        if angle == 90:
            rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif angle == 180:
            rotated_image = cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            rotated_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            rotated_image = image.copy()
        
        # Step 3: Text detection on rotated image
        detections = self.det_model.detect(rotated_image, conf_threshold=conf_threshold, use_close=use_close)
        
        # Step 4: Text recognition for each detected region
        results = []
        for det in detections:
            bbox = det['bbox']
            x1, y1, x2, y2 = bbox
            
            # Crop text region
            cropped = rotated_image[y1:y2, x1:x2]
            if cropped.size == 0:
                continue
            
            # Recognize text
            rec_result = self.rec_model.recognize(cropped, conf_threshold=conf_threshold)
            
            # Combine results
            result = {
                'text': rec_result['text'],
                'bbox': bbox,
                'confidence': rec_result['confidence'],
                'text_region_confidence': det['confidence'],
                'rotation': angle,
                'rotation_confidence': rotation_confidence
            }
            results.append(result)
        
        return results

    def load(self) -> bool:
        """
        Load the OCR pipeline models.
        
        Returns:
            bool: True if loading successful, False otherwise
        """
        try:
            if self.is_loaded():
                print("Models already loaded")
                return True
            
            print("Loading PP-OCRv5 Pipeline models...")
            
            # Initialize orientation classifier
            self.cls_model = PPLCNetDocONNX(model_path=self.cls_model_path, use_gpu=self.use_gpu, gpu_id=self.gpu_id)
            
            # Initialize text detector
            self.det_model = PPOCRv5DetONNX(model_path=self.det_model_path, use_gpu=self.use_gpu, gpu_id=self.gpu_id)
            
            # Initialize text recognizer
            self.rec_model = PPOCRv5RecONNX(model_path=self.rec_model_path, use_gpu=self.use_gpu, gpu_id=self.gpu_id)
            
            print("PP-OCRv5 Pipeline models loaded successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to load PPOCRv5Pipeline models: {e}")
            # Clean up any partially loaded models
            self.unload()
            return False

    def unload(self) -> bool:
        """
        Unload the OCR pipeline models to free memory.
        
        Returns:
            bool: True if successful
        """
        try:
            # Clean up model instances
            if hasattr(self, 'cls_model') and self.cls_model is not None:
                del self.cls_model
                self.cls_model = None
            
            if hasattr(self, 'det_model') and self.det_model is not None:
                del self.det_model
                self.det_model = None
                
            if hasattr(self, 'rec_model') and self.rec_model is not None:
                del self.rec_model
                self.rec_model = None
                
            return True
        except Exception as e:
            print(f"Failed to unload PPOCRv5Pipeline models: {e}")
            return False

    def is_loaded(self) -> bool:
        """
        Check if the pipeline models are loaded.
        
        Returns:
            bool: True if all models are loaded
        """
        return (hasattr(self, 'cls_model') and self.cls_model is not None and
                hasattr(self, 'det_model') and self.det_model is not None and
                hasattr(self, 'rec_model') and self.rec_model is not None)

    def visualize(self, image: np.ndarray, results: List[Dict], output_path: str = None, cls_thresh: float = 0.9, use_cls: bool = True) -> np.ndarray:
        """
        Visualize OCR results on image
        
        Args:
            image: Original input image
            results: OCR results from ocr() method
            output_path: Path to save visualization (optional)
            cls_thresh: Confidence threshold for classification
            use_cls: Whether to use document orientation classification
            
        Returns:
            Image with OCR results drawn
        """
        if not self.is_loaded():
            print("PP-OCRv5 models not loaded, auto-loading...")
            if not self.load():
                raise RuntimeError("Failed to auto-load PP-OCRv5 models.")
            
        # First, apply the same rotation as in ocr()
        angle = 0
        if use_cls:
            cls_result = self.cls_model.classify(image)
            if cls_result['confidence'] >= cls_thresh:
                angle = int(cls_result['angle'])
            else:
                angle = 0
        else:
            angle = 0
        
        if angle == 90:
            vis_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif angle == 180:
            vis_image = cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            vis_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            vis_image = image.copy()
        
        # Draw results
        for result in results:
            bbox = result['bbox']
            text = result['text']
            conf = result['confidence']
            
            # Draw bounding box
            cv2.rectangle(vis_image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            
            # Draw text
            label = f"{text} ({conf:.2f})"
            cv2.putText(vis_image, label, (bbox[0], bbox[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Add orientation info
        orientation_text = f"Orientation: {angle}°"
        cv2.putText(vis_image, orientation_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, vis_image)
            print(f"Visualization saved to {output_path}")
        
        return vis_image

    def get_pipeline_info(self) -> Dict:
        """
        Get information about all models in the pipeline
        
        Returns:
            Dictionary with model configurations
        """
        if not self.is_loaded():
            return {
                'status': 'not_loaded',
                'message': 'Models not loaded yet. Call load() first.'
            }
            
        return {
            'status': 'loaded',
            'orientation_model': self.cls_model.get_config_info(),
            'detection_model': self.det_model.get_config_info(),
            'recognition_model': self.rec_model.get_config_info()
        }


def main():
    """Example usage of PP-OCRv5 Pipeline"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pp_ocrv5_pipeline_new.py <image_path> [output_path]")
        return
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Initialize pipeline
    pipeline = PPOCRv5Pipeline()
    
    # Load models
    if not pipeline.load():
        print("Failed to load models")
        return
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load image: {image_path}")
        return
    
    # Run OCR
    results = pipeline.ocr(image, conf_threshold=0.5)
    
    print(f"Found {len(results)} text regions:")
    for i, result in enumerate(results):
        print(f"  Region {i}: '{result['text']}' (conf: {result['confidence']:.2f})")
    
    # Visualize
    if output_path:
        vis_image = pipeline.visualize(image, results, output_path)
    else:
        vis_image = pipeline.visualize(image, results)
        cv2.imshow("PP-OCRv5 Pipeline Results", vis_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()