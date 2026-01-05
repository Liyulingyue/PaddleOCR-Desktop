"""
Standalone PP-OCRv5 Orientation Classification ONNX Inference
Implements document orientation detection using PP-LCNet_x1_0_doc_ori ONNX model
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple
import yaml

from .onnx_model_base import ONNXModelBase
from ...config import get_model_path_from_registry


class PPLCNetDocONNX(ONNXModelBase):
    def __init__(self, model_path: str = None, use_gpu: bool = False, gpu_id: int = 0):
        """
        Initialize PP-OCRv5 Classification ONNX model

        Args:
            model_path: Path to the ONNX model file. If None, uses default path.
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        if model_path is None:
            # Use unified model path resolution
            model_dir = get_model_path_from_registry("PP-LCNet_x1_0_doc_ori-ONNX")
            if model_dir is None:
                raise FileNotFoundError("PP-LCNet_x1_0_doc_ori-ONNX model not found in registry")
            model_path = model_dir

        self.model_path = Path(model_path) / 'inference.onnx'
        self.yml_path = Path(model_path) / 'inference.yml'
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        if not self.yml_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {self.yml_path}")

        with open(self.yml_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Extract information from config
        self.label_list = self.config.get('PostProcess', {}).get('Topk', {}).get('label_list', ['0', '90', '180', '270'])
        self.model_name = self.config.get('Global', {}).get('model_name', 'Unknown')

        # Extract preprocessing config
        self.resize_short = 256  # Default
        self.crop_size = 224     # Default
        self.mean = [0.485, 0.456, 0.406]  # ImageNet default
        self.std = [0.229, 0.224, 0.225]   # ImageNet default
        preprocess_config = self.config.get('PreProcess', {}).get('transform_ops', [])
        for step in preprocess_config:
            if 'ResizeImage' in step:
                self.resize_short = step['ResizeImage'].get('resize_short', 256)
            elif 'CropImage' in step:
                self.crop_size = step['CropImage'].get('size', 224)
            elif 'NormalizeImage' in step:
                self.mean = step['NormalizeImage'].get('mean', [0.485, 0.456, 0.406])
                self.std = step['NormalizeImage'].get('std', [0.229, 0.224, 0.225])

        # Extract dynamic shape information for reference
        self.dynamic_shapes = {}
        backend_configs = self.config.get('Hpi', {}).get('backend_configs', {})
        if 'paddle_infer' in backend_configs and 'trt_dynamic_shapes' in backend_configs['paddle_infer']:
            self.dynamic_shapes = backend_configs['paddle_infer']['trt_dynamic_shapes']
        elif 'tensorrt' in backend_configs and 'dynamic_shapes' in backend_configs['tensorrt']:
            self.dynamic_shapes = backend_configs['tensorrt']['dynamic_shapes']

        # Initialize ONNXModelBase
        super().__init__(model_path=str(self.model_path), use_gpu=use_gpu, gpu_id=gpu_id)

        print(f"Loaded {self.model_name} model with {len(self.label_list)} classes: {self.label_list}")

    def get_config_info(self) -> Dict:
        """
        Get configuration information loaded from yml file

        Returns:
            Dictionary containing configuration details
        """
        return {
            'model_name': self.model_name,
            'resize_short': self.resize_short,
            'crop_size': self.crop_size,
            'mean': self.mean,
            'std': self.std,
            'num_classes': len(self.label_list),
            'label_list': self.label_list,
            'dynamic_shapes': self.dynamic_shapes,
            'input_names': self.input_names,
            'input_shapes': self.input_shapes
        }

    def preprocess(self, image: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        """
        Preprocess image for PP-OCRv5 Classification model

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with preprocessed inputs for ONNX model
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")

        # Resize image with short side to resize_short
        h, w = image.shape[:2]
        if h < w:
            new_h = self.resize_short
            new_w = int(w * (new_h / h))
        else:
            new_w = self.resize_short
            new_h = int(h * (new_w / w))
        resized = cv2.resize(image, (new_w, new_h))

        # Center crop to crop_size
        crop_h, crop_w = self.crop_size, self.crop_size
        start_h = (new_h - crop_h) // 2
        start_w = (new_w - crop_w) // 2
        cropped = resized[start_h:start_h + crop_h, start_w:start_w + crop_w]

        # Normalize using config values
        normalized = cropped.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std

        # Convert to CHW format
        chw = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension
        batch_input = np.expand_dims(chw, 0)

        # Return inputs dict for ONNX model - PP-OCRv5 cls expects 'x'
        inputs = {
            'x': batch_input.astype(np.float32),  # [1, 3, 224, 224]
        }

        return inputs

    def postprocess(self, outputs: List[np.ndarray], image: np.ndarray, original_size: Tuple[int, int], conf_threshold: float = 0.5) -> List[Dict]:
        """
        Postprocess model outputs for classification

        Args:
            outputs: Model outputs [batch, num_classes]
            original_size: Original image size (not used for cls)
            conf_threshold: Confidence threshold (not used for cls)

        Returns:
            List of classification results with angle and confidence
        """
        preds = outputs[0]  # [batch, num_classes]

        # Get top 1 prediction
        pred_idx = np.argmax(preds, axis=1)[0]
        pred_prob = np.max(preds, axis=1)[0]

        angle = self.label_list[pred_idx]
        confidence = float(pred_prob)

        result = {
            'angle': angle,
            'confidence': confidence
        }

        return [result]

    def classify(self, image: np.ndarray) -> Dict:
        """
        Run document orientation classification on input image

        Args:
            image: Input image

        Returns:
            Classification result with angle and confidence
        """
        # Get original size for postprocessing
        original_size = (image.shape[1], image.shape[0])  # w, h

        # Use ONNXModelBase.run method which handles preprocess -> infer -> postprocess
        results = self.run(image, original_size=original_size, conf_threshold=0.5)

        # Return the first result
        return results[0] if results else {'angle': '0', 'confidence': 0.0}

    def visualize(self, image: np.ndarray, result: Dict, output_path: str = None) -> np.ndarray:
        """
        Visualize classification result on image

        Args:
            image: Original image
            result: Classification result
            output_path: Path to save visualization (optional)

        Returns:
            Image with text overlay
        """
        vis_image = image.copy()

        angle = result.get('angle', '0')
        conf = result.get('confidence', 0.0)

        # Draw text on image
        label_text = f"Orientation: {angle}° (conf: {conf:.2f})"
        cv2.putText(vis_image, label_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if output_path:
            cv2.imwrite(output_path, vis_image)
            print(f"Visualization saved to {output_path}")

        return vis_image


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pp_ocrv5cls_onnx_new.py <image_path> [output_path]")
        return

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize classifier
    classifier = PPLCNetDocONNX()

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load image: {image_path}")
        return

    # Run classification
    result = classifier.classify(image)

    print(f"Detected orientation: {result['angle']}°")
    print(f"Confidence: {result['confidence']}")

    # Visualize
    if output_path:
        vis_image = classifier.visualize(image, result, output_path)
    else:
        vis_image = classifier.visualize(image, result)
        cv2.imshow("PP-OCRv5 Classification", vis_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()