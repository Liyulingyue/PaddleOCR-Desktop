"""
Standalone PP-OCRv5 Recognition ONNX Inference
Implements text recognition using PP-OCRv5 mobile rec ONNX model
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple
import yaml

from .onnx_model_base import ONNXModelBase
from ...config import get_model_path_from_registry


class PPOCRv5RecONNX(ONNXModelBase):
    def __init__(self, model_path: str = None, use_gpu: bool = False, gpu_id: int = 0):
        """
        Initialize PP-OCRv5 Recognition ONNX model

        Args:
            model_path: Path to the ONNX model file. If None, uses default path.
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        if model_path is None:
            # Use unified model path resolution
            model_dir = get_model_path_from_registry("PP-OCRv5_mobile_rec-ONNX")
            if model_dir is None:
                raise FileNotFoundError("PP-OCRv5_mobile_rec-ONNX model not found in registry")
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
        self.label_list = self.config.get('PostProcess', {}).get('character_dict', [])
        self.postprocess_name = self.config.get('PostProcess', {}).get('name', 'CTCLabelDecode')
        self.model_name = self.config.get('Global', {}).get('model_name', 'Unknown')

        # Extract preprocessing config
        self.target_size = (320, 48)  # Default for PP-OCRv5 rec
        self.mean = [0.5, 0.5, 0.5]    # Default
        self.std = [0.5, 0.5, 0.5]     # Default
        preprocess_config = self.config.get('PreProcess', {}).get('transform_ops', [])
        for step in preprocess_config:
            if 'RecResizeImg' in step:
                image_shape = step['RecResizeImg'].get('image_shape', [3, 48, 320])
                self.target_size = (image_shape[2], image_shape[1])  # (W, H)
            # NormalizeImage not specified in config, use defaults

        if not self.label_list:
            self.label_list = [' ']  # Default blank for CTC

        # Extract dynamic shape information for reference
        self.dynamic_shapes = {}
        backend_configs = self.config.get('Hpi', {}).get('backend_configs', {})
        if 'paddle_infer' in backend_configs and 'trt_dynamic_shapes' in backend_configs['paddle_infer']:
            self.dynamic_shapes = backend_configs['paddle_infer']['trt_dynamic_shapes']
        elif 'tensorrt' in backend_configs and 'dynamic_shapes' in backend_configs['tensorrt']:
            self.dynamic_shapes = backend_configs['tensorrt']['dynamic_shapes']

        # Initialize ONNXModelBase
        super().__init__(model_path=str(self.model_path), use_gpu=use_gpu, gpu_id=gpu_id)

        print(f"Loaded {self.model_name} model with {len(self.label_list)} classes")
        # print(f"Classes: {self.label_list}")

    def get_config_info(self) -> Dict:
        """
        Get configuration information loaded from yml file

        Returns:
            Dictionary containing configuration details
        """
        return {
            'model_name': self.model_name,
            'target_size': self.target_size,
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
        Preprocess image for PP-OCRv5 Recognition model

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

        # Calculate target size maintaining aspect ratio
        target_h = 48
        target_w = int(w * (target_h / h))
        
        # Limit max width to prevent excessive memory usage (from dynamic shapes max ~3200)
        max_w = 3200
        target_w = min(target_w, max_w)
        
        # Ensure minimum width
        # min_w = 160
        min_w = target_h  # From dynamic shapes min
        target_w = max(target_w, min_w)  # From dynamic shapes min

        # Resize to target size maintaining aspect ratio
        resized = cv2.resize(image, (target_w, target_h))

        # Normalize using config values (0.5 mean, 0.5 std)
        normalized = resized.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std

        # Convert to CHW format
        chw = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension
        batch_input = np.expand_dims(chw, 0)

        # Return inputs dict for ONNX model - PP-OCRv5 rec expects 'x'
        inputs = {
            'x': batch_input.astype(np.float32),  # [1, 3, 48, 320]
        }

        return inputs

    def postprocess(self, outputs: List[np.ndarray], image: np.ndarray, original_size: Tuple[int, int], conf_threshold: float = 0.5) -> List[Dict]:
        """
        Postprocess model outputs using CTC decoding similar to existing pipeline

        Args:
            outputs: Model outputs [batch, seq_len, num_classes] or [batch, seq_len]
            original_size: Original image size (w, h) (not used for rec)
            conf_threshold: Confidence threshold (not used for rec)

        Returns:
            List of recognized text with confidence
        """
        preds = outputs[0]  # [batch, seq_len, num_classes] or [batch, seq_len]

        if len(preds.shape) == 3:
            # [batch, seq_len, num_classes]
            preds_idx = preds.argmax(axis=2)  # [batch, seq_len]
            preds_prob = preds.max(axis=2)    # [batch, seq_len]
        elif len(preds.shape) == 2:
            # [batch, seq_len] already indices
            preds_idx = preds
            preds_prob = np.ones_like(preds, dtype=float)  # Assume confidence 1.0
        else:
            raise ValueError(f"Unexpected preds shape: {preds.shape}")

        # Decode for batch_idx 0
        text_index = preds_idx[0]
        text_prob = preds_prob[0]

        # CTC decoding: remove duplicates and blanks (0 is blank)
        selection = np.ones(len(text_index), dtype=bool)
        selection[1:] = text_index[1:] != text_index[:-1]  # Remove consecutive duplicates
        selection &= text_index != 0  # Remove blank (0)

        char_list = []
        conf_list = []
        for idx, prob in zip(text_index[selection], text_prob[selection]):
            if 0 < idx < len(self.label_list) + 1:  # Valid character index (skip blank)
                char_list.append(self.label_list[idx - 1])  # -1 because blank is 0
                conf_list.append(prob)

        if len(conf_list) == 0:
            conf_list = [0]

        recognized_text = "".join(char_list)
        confidence = float(np.mean(conf_list))

        result = {
            'text': recognized_text,
            'confidence': confidence
        }

        return [result]

    def recognize(self, image: np.ndarray, conf_threshold: float = 0.5) -> Dict:
        """
        Run text recognition on input image

        Args:
            image: Input image
            conf_threshold: Confidence threshold for recognition

        Returns:
            Recognized text and confidence
        """
        # Get original size for postprocessing
        original_size = (image.shape[1], image.shape[0])  # w, h

        # Use ONNXModelBase.run method which handles preprocess -> infer -> postprocess
        results = self.run(image, original_size=original_size, conf_threshold=conf_threshold)

        # Return the first result
        return results[0] if results else {'text': '', 'confidence': 0.0}

    def visualize(self, image: np.ndarray, result: Dict, output_path: str = None) -> np.ndarray:
        """
        Visualize recognized text on image

        Args:
            image: Original image
            result: Recognition result
            output_path: Path to save visualization (optional)

        Returns:
            Image with text overlay
        """
        vis_image = image.copy()

        text = result.get('text', '')
        conf = result.get('confidence', 0.0)

        # Draw text on image
        label_text = f"Text: {text} (conf: {conf:.2f})"
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
        print("Usage: python pp_ocrv5rec_onnx_new.py <image_path> [output_path]")
        return

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize recognizer
    recognizer = PPOCRv5RecONNX()

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load image: {image_path}")
        return

    # Run recognition
    result = recognizer.recognize(image, conf_threshold=0.5)

    print(f"Recognized text: {result['text']}")
    print(f"Confidence: {result['confidence']}")

    # Visualize
    if output_path:
        vis_image = recognizer.visualize(image, result, output_path)
    else:
        vis_image = recognizer.visualize(image, result)
        cv2.imshow("PP-OCRv5 Recognition", vis_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()