"""
Standalone PP-OCRv5 Detection ONNX Inference
Implements text detection using PP-OCRv5 mobile det ONNX model
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple
import yaml
from shapely.geometry import Polygon

from .onnx_model_base import ONNXModelBase
from ...config import get_model_path_from_registry


class PPOCRv5DetONNX(ONNXModelBase):
    def __init__(self, model_path: str = None, use_gpu: bool = False, gpu_id: int = 0):
        """
        Initialize PP-OCRv5 Detection ONNX model

        Args:
            model_path: Path to the ONNX model file. If None, uses default path.
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        if model_path is None:
            # Use unified model path resolution
            model_dir = get_model_path_from_registry("PP-OCRv5_mobile_det-ONNX")
            if model_dir is None:
                raise FileNotFoundError("PP-OCRv5_mobile_det-ONNX model not found in registry")
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
        self.label_list = self.config.get('label_list', [])
        self.draw_threshold = self.config.get('draw_threshold', 0.5)
        self.arch = self.config.get('arch', 'Unknown')
        self.model_name = self.config.get('Global', {}).get('model_name', 'Unknown')

        # Extract preprocessing config
        self.target_size = (960, 960)  # Default for PP-OCRv5 det
        self.mean = [0.485, 0.456, 0.406]    # Default ImageNet mean
        self.std = [0.229, 0.224, 0.225]     # Default ImageNet std
        preprocess_config = self.config.get('PreProcess', {}).get('transform_ops', [])
        for step in preprocess_config:
            if 'DetResizeForTest' in step:
                resize_long = step['DetResizeForTest'].get('resize_long', 960)
                self.target_size = (resize_long, resize_long)
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

        # Extract postprocessing config
        self.thresh = self.config.get('PostProcess', {}).get('thresh', 0.3) if self.config else 0.3
        self.box_thresh = self.config.get('PostProcess', {}).get('box_thresh', 0.6) if self.config else 0.6
        self.max_candidates = self.config.get('PostProcess', {}).get('max_candidates', 1000) if self.config else 1000
        self.unclip_ratio = self.config.get('PostProcess', {}).get('unclip_ratio', 1.5) if self.config else 1.5

        if not self.label_list:
            self.label_list = ['text']  # Default for detection

        # Initialize ONNXModelBase
        super().__init__(model_path=str(self.model_path), use_gpu=use_gpu, gpu_id=gpu_id)

        print(f"Loaded {self.model_name} ({self.arch}) model with {len(self.label_list)} classes")
        # print(f"Classes: {self.label_list}")

    @staticmethod
    def align_to_multiple(size: int, multiple: int) -> int:
        """Align size to nearest multiple (floor division)"""
        return (size // multiple) * multiple

    def unclip(self, box, unclip_ratio):
        """
        Expand polygon using shapely (simplified version of PaddleOCR's unclip)
        """
        poly = Polygon(box)
        distance = poly.area * unclip_ratio / poly.length
        expanded = poly.buffer(distance)
        if expanded.is_empty:
            return box
        # Get the exterior coordinates
        expanded_coords = list(expanded.exterior.coords)
        return np.array(expanded_coords[:-1], dtype=np.int32)  # Remove closing point

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
            'input_shapes': self.input_shapes,
            'dynamic_shapes': self.dynamic_shapes,  # Reference dynamic shape configurations
            'thresh': self.thresh,
            'box_thresh': self.box_thresh,
            'max_candidates': self.max_candidates,
            'unclip_ratio': self.unclip_ratio,
        }

    def preprocess(self, image: np.ndarray, min_size: int = 32, max_size: int = 4000, align_size: int = 32, **kwargs) -> Tuple[Dict[str, np.ndarray], Dict[str, any]]:
        """
        Preprocess image for PP-OCRv5 Detection model

        Args:
            image: Input image (BGR format)
            min_size: Minimum size constraint
            max_size: Maximum size constraint
            align_size: Alignment multiple

        Returns:
            Tuple of (inputs_dict, preprocess_info)
            - inputs_dict: Dictionary with preprocessed inputs for ONNX model
            - preprocess_info: Dictionary with preprocessing metadata for postprocessing
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")

        # Align the input parameters to align_size multiples
        min_size = ((min_size + align_size - 1) // align_size) * align_size
        max_size = (max_size // align_size) * align_size

        # Get original size
        h, w = image.shape[:2]
        original_size = (w, h)  # Store for postprocessing

        # Dynamic sizing: constrain to [min_size, max_size] and align to nearest align_size multiple

        # Step 1: Get bounded size (ensure within [min_size, max_size])
        bounded_w = max(min_size, min(max_size, w))
        bounded_h = max(min_size, min(max_size, h))

        # Step 2: Align bounded size to align_size multiples
        new_w = self.align_to_multiple(bounded_w, align_size)
        new_h = self.align_to_multiple(bounded_h, align_size)

        # Ensure minimum size after alignment
        new_w = max(new_w, min_size)
        new_h = max(new_h, min_size)

        # Step 3: Calculate final resize scale after size computation is complete
        resize_scale = (new_w / w, new_h / h)
        resize_offset = (0, 0)  # No offset since we place at top-left

        # Resize image
        resized = cv2.resize(image, (new_w, new_h))

        # Use resized image directly (assuming model supports non-square input)
        final_image = resized

        # Normalize using config values
        normalized = final_image.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std

        # Convert to CHW format
        chw = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension
        batch_input = np.expand_dims(chw, 0)

        # Return inputs dict for ONNX model - PP-OCRv5 det expects 'x'
        inputs = {
            'x': batch_input.astype(np.float32),  # [1, 3, H, W]
        }

        # Return preprocessing metadata for postprocessing
        preprocess_info = {
            'original_size': original_size,
            'resize_scale': resize_scale,
            'resize_offset': resize_offset,
        }

        return inputs, preprocess_info

    def run_inference(self, inputs: Dict[str, np.ndarray]) -> List[np.ndarray]:
        """
        Run ONNX inference

        Args:
            inputs: Preprocessed inputs dictionary

        Returns:
            Raw model outputs
        """
        return self.session.run(self.output_names, input_feed=inputs)

    def postprocess(self, outputs: List[np.ndarray], preprocess_info: Dict[str, any], conf_threshold: float = 0.5, use_open: bool = False, use_close: bool = False, morph_kernel_size: int = 3) -> List[Dict]:
        """
        Postprocess model outputs using DBPostProcess for text detection

        Args:
            outputs: Model outputs [batch, 1, H, W] probability map
            preprocess_info: Preprocessing metadata from preprocess method
            conf_threshold: Confidence threshold

        Returns:
            List of detected text regions with bbox
        """
        pred = outputs[0][0, 0]  # [H, W] probability map

        # Binary thresholding
        binary = (pred > self.thresh).astype(np.uint8)

        # Optional morphological operations to clean up
        kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)
        if use_close:
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        if use_open:
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        orig_w, orig_h = preprocess_info['original_size']
        resize_scale = preprocess_info['resize_scale']

        for contour in contours:
            # Get minimum area rectangle (like original PaddleOCR)
            rect = cv2.minAreaRect(contour)
            points = cv2.boxPoints(rect)
            points = np.array(points, dtype=np.int32)

            # Get box dimensions
            width, height = rect[1]
            if width < 5 or height < 5:
                continue

            # Apply unclip expansion (like original PaddleOCR)
            expanded_points = self.unclip(points, self.unclip_ratio)

            # Get final bbox from expanded polygon
            x, y, w, h = cv2.boundingRect(expanded_points)

            # Calculate confidence as mean probability in the region
            mask = np.zeros_like(pred, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 1, -1)
            confidence = float(np.mean(pred[mask > 0]))

            if confidence < conf_threshold:
                continue

            # Map coordinates back to original image
            # The model outputs coordinates relative to the square canvas input
            # We placed the resized image at (0,0) on the canvas
            # So coordinates within the resized image area are valid
            # Scale back to original image coordinates
            x_orig = x / resize_scale[0]
            y_orig = y / resize_scale[1]
            w_orig = w / resize_scale[0]
            h_orig = h / resize_scale[1]

            # Clip to original image boundaries
            x_orig = max(0, min(x_orig, orig_w - 1))
            y_orig = max(0, min(y_orig, orig_h - 1))
            w_orig = min(w_orig, orig_w - x_orig)
            h_orig = min(h_orig, orig_h - y_orig)

            bbox = [int(x_orig), int(y_orig), int(x_orig + w_orig), int(y_orig + h_orig)]

            region = {
                'bbox': bbox,
                'type': 'text',
                'confidence': confidence
            }
            regions.append(region)

        # Limit number of candidates
        regions = sorted(regions, key=lambda x: x['confidence'], reverse=True)
        regions = regions[:self.max_candidates]

        return regions

    def detect(self, image: np.ndarray, conf_threshold: float = 0.5, use_open: bool = False, use_close: bool = False, morph_kernel_size: int = 3) -> List[Dict]:
        """
        Run text detection on input image

        Args:
            image: Input image
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detected text regions
        """
        # Preprocess image and get metadata
        inputs, preprocess_info = self.preprocess(image)

        # Run inference
        outputs = self.run_inference(inputs)

        # Postprocess with metadata
        regions = self.postprocess(outputs, preprocess_info, conf_threshold, use_open, use_close, morph_kernel_size)

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
        print("Usage: python pp_ocrv5det_onnx_new.py <image_path> [output_path]")
        return

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize detector
    detector = PPOCRv5DetONNX()

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
        cv2.imshow("PP-OCRv5 Detection", vis_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()