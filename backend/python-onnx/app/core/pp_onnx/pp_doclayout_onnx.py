"""
Standalone PP-DocLayout ONNX Inference
Implements layout detection using PP-DocLayout-L ONNX model
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple
import yaml

from .onnx_model_base import ONNXModelBase


class PPDocLayoutONNX(ONNXModelBase):
    def __init__(self, model_path: str = None, use_gpu: bool = False, gpu_id: int = 0):
        """
        Initialize PP-DocLayout ONNX model

        Args:
            model_path: Path to the ONNX model file. If None, uses default path.
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        if model_path is None:
            # Default path relative to project root
            import os
            project_root = Path(__file__).parent.parent.parent.parent.parent  # backend/python-onnx/app/core -> project root
            model_path = project_root / 'backend' / 'python-onnx' / 'models' / 'pp_structure_v3' / 'PP-DocLayout-L' / 'inference.onnx'

        self.model_path = Path(model_path)
        self.yml_path = self.model_path.parent / 'inference.yml'
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        if not self.yml_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {self.yml_path}")

        with open(self.yml_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Extract information from config
        self.label_list = self.config.get('label_list', [])
        self.draw_threshold = self.config.get('draw_threshold', 0.5)
        self.arch = self.config.get('arch', 'Unknown')
        self.model_name = self.config.get('Global', {}).get('model_name', 'Unknown')

        # Extract preprocessing config
        self.target_size = (640, 640)  # Default
        self.mean = [0.0, 0.0, 0.0]    # Default
        self.std = [1.0, 1.0, 1.0]     # Default
        preprocess_config = self.config.get('Preprocess', [])
        for step in preprocess_config:
            if step.get('type') == 'Resize':
                target_size = step.get('target_size', [640, 640])
                self.target_size = tuple(target_size)
            elif step.get('type') == 'NormalizeImage':
                self.mean = step.get('mean', [0.0, 0.0, 0.0])
                self.std = step.get('std', [1.0, 1.0, 1.0])

        if not self.label_list:
            raise ValueError("No label_list found in inference.yml")

        # Initialize ONNXModelBase
        super().__init__(model_path=str(self.model_path), use_gpu=use_gpu, gpu_id=gpu_id)

        print(f"Loaded {self.model_name} ({self.arch}) model with {len(self.label_list)} classes")
        # print(f"Classes: {self.label_list}")

    def get_config_info(self) -> Dict:
        """
        Get configuration information loaded from yml file

        Returns:
            Dictionary containing configuration details
        """
        return {
            'model_name': self.model_name,
            'arch': self.arch,
            'draw_threshold': self.draw_threshold,
            'target_size': self.target_size,
            'mean': self.mean,
            'std': self.std,
            'num_classes': len(self.label_list),
            'label_list': self.label_list,
            'input_names': self.input_names,
            'input_shapes': self.input_shapes
        }

    def preprocess(self, image: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        """
        Preprocess image for PP-DocLayout model

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with preprocessed inputs for ONNX model
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")

        # Get original size
        h, w = image.shape[:2]

        # Resize to target size (from config) - stretches to fill the canvas
        resized = cv2.resize(image, self.target_size)

        # Normalize using config values
        normalized = resized.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std

        # Convert to CHW format
        chw = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension
        batch_input = np.expand_dims(chw, 0)

        # Calculate scale factors for coordinate conversion
        scale_w = self.target_size[0] / w
        scale_h = self.target_size[1] / h

        # Return inputs dict for ONNX model
        inputs = {
            'im_shape': np.array([self.target_size], dtype=np.float32),  # [1, 2]
            'image': batch_input.astype(np.float32),  # [1, 3, H, W]
            'scale_factor': np.array([[scale_h, scale_w]], dtype=np.float32)  # [1, 2]
        }

        return inputs

    def postprocess(self, outputs: List[np.ndarray], image: np.ndarray, original_size: Tuple[int, int], conf_threshold: float = 0.5) -> List[Dict]:
        """
        Postprocess model outputs to get layout regions

        Args:
            outputs: Model outputs
            original_size: Original image size (w, h)
            conf_threshold: Confidence threshold

        Returns:
            List of detected regions with bbox, type, confidence
        """
        # For PP-DocLayout, outputs[0] is [num_detections, 6] where 6 = [class_id, score, x1, y1, x2, y2]
        detections = outputs[0]  # Shape: (300, 6)

        regions = []
        orig_w, orig_h = original_size

        for det in detections:
            # Format: [class_id, score, x1, y1, x2, y2]
            class_id, score, x1, y1, x2, y2 = det

            if score < conf_threshold:
                continue

            # Convert to int for class_id
            class_idx = int(class_id)

            if class_idx >= len(self.label_list):
                continue

            # Model already outputs coordinates in original image coordinate system
            # No additional scaling needed

            # Clip to image boundaries
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))

            # Skip invalid boxes
            if x2 <= x1 or y2 <= y1:
                continue

            region = {
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'type': self.label_list[class_idx],
                'confidence': float(score)
            }
            regions.append(region)

        return regions

    def detect(self, image: np.ndarray, conf_threshold: float = 0.5) -> List[Dict]:
        """
        Run layout detection on input image

        Args:
            image: Input image
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detected layout regions
        """
        # Get original size for postprocessing
        original_size = (image.shape[1], image.shape[0])  # w, h

        # Use ONNXModelBase.run method which handles preprocess -> infer -> postprocess
        regions = self.run(image, original_size=original_size, conf_threshold=conf_threshold)

        return regions

    def visualize(self, image: np.ndarray, regions: List[Dict], output_path: str = None) -> np.ndarray:
        """
        Visualize detected regions on image

        Args:
            image: Original image
            regions: Detected regions
            output_path: Path to save visualization (optional)

        Returns:
            Image with visualizations
        """
        vis_image = image.copy()

        # Color map for different types
        colors = {
            'text': (0, 255, 0),      # Green
            'table': (255, 0, 0),     # Blue
            'image': (0, 0, 255),     # Red
            'formula': (255, 255, 0), # Cyan
            'chart': (255, 0, 255),   # Magenta
            'header': (0, 255, 255),  # Yellow
            'footer': (128, 128, 128),# Gray
        }

        for region in regions:
            bbox = region['bbox']
            label = region['type']
            conf = region['confidence']

            color = colors.get(label, (255, 255, 255))  # White for unknown

            # Draw rectangle
            cv2.rectangle(vis_image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

            # Draw label
            label_text = f"{label}: {conf:.2f}"
            cv2.putText(vis_image, label_text, (bbox[0], bbox[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        if output_path:
            cv2.imwrite(output_path, vis_image)
            print(f"Visualization saved to {output_path}")

        return vis_image


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pp_doclayout_onnx.py <image_path> [output_path]")
        return

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize detector
    detector = PPDocLayoutONNX()

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load image: {image_path}")
        return

    # Run detection
    regions = detector.detect(image, conf_threshold=0.3)

    print(f"Detected {len(regions)} regions:")
    for region in regions:
        print(f"  {region}")

    # Visualize
    if output_path:
        vis_image = detector.visualize(image, regions, output_path)
    else:
        vis_image = detector.visualize(image, regions)
        cv2.imshow("PP-DocLayout Detection", vis_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()