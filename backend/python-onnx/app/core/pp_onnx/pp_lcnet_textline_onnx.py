"""
PP-LCNet TextLine Orientation Classification ONNX Inference
Implements textline orientation detection (0°/180°) using PP-LCNet_x1_0_textline_ori ONNX model
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import yaml

from .onnx_model_base import ONNXModelBase
from ...config import get_model_path_from_registry


class PPLCNetTextLineONNX(ONNXModelBase):
    def __init__(self, model_path: str = None, use_gpu: bool = False, gpu_id: int = 0):
        """
        Initialize TextLine Orientation Classification ONNX model

        Args:
            model_path: Path to the ONNX model directory. If None, uses default path.
            use_gpu: Whether to use GPU
            gpu_id: GPU device ID
        """
        if model_path is None:
            model_dir = get_model_path_from_registry("PP-LCNet_x1_0_textline_ori-ONNX")
            if model_dir is None:
                raise FileNotFoundError("PP-LCNet_x1_0_textline_ori-ONNX model not found in registry")
            model_path = model_dir

        self.model_path = Path(model_path) / 'inference.onnx'
        self.yml_path = Path(model_path) / 'inference.yml'
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        if not self.yml_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {self.yml_path}")

        with open(self.yml_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.label_list = self.config.get('PostProcess', {}).get('Topk', {}).get('label_list', ['0', '180'])
        self.model_name = self.config.get('Global', {}).get('model_name', 'Unknown')

        self.resize_short = 256
        self.crop_size = 224
        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]
        preprocess_config = self.config.get('PreProcess', {}).get('transform_ops', [])
        for step in preprocess_config:
            if 'ResizeImage' in step:
                self.resize_short = step['ResizeImage'].get('resize_short', 256)
            elif 'CropImage' in step:
                self.crop_size = step['CropImage'].get('size', 224)
            elif 'NormalizeImage' in step:
                self.mean = step['NormalizeImage'].get('mean', [0.485, 0.456, 0.406])
                self.std = step['NormalizeImage'].get('std', [0.229, 0.224, 0.225])

        super().__init__(model_path=str(self.model_path), use_gpu=use_gpu, gpu_id=gpu_id)

        print(f"Loaded {self.model_name} textline orientation model with {len(self.label_list)} classes: {self.label_list}")

    def get_config_info(self) -> Dict:
        return {
            'model_name': self.model_name,
            'resize_short': self.resize_short,
            'crop_size': self.crop_size,
            'mean': self.mean,
            'std': self.std,
            'num_classes': len(self.label_list),
            'label_list': self.label_list,
            'input_names': self.input_names,
            'input_shapes': self.input_shapes
        }

    def preprocess(self, image: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")

        h, w = image.shape[:2]
        if h < w:
            new_h = self.resize_short
            new_w = int(w * (new_h / h))
        else:
            new_w = self.resize_short
            new_h = int(h * (new_w / w))
        resized = cv2.resize(image, (new_w, new_h))

        crop_h, crop_w = self.crop_size, self.crop_size
        start_h = (new_h - crop_h) // 2
        start_w = (new_w - crop_w) // 2
        cropped = resized[start_h:start_h + crop_h, start_w:start_w + crop_w]

        normalized = cropped.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std
        chw = np.transpose(normalized, (2, 0, 1))
        batch_input = np.expand_dims(chw, 0)

        return {'x': batch_input.astype(np.float32)}

    def postprocess(self, outputs: List[np.ndarray], image: np.ndarray, original_size: Tuple[int, int], conf_threshold: float = 0.5) -> List[Dict]:
        preds = outputs[0]
        pred_idx = np.argmax(preds, axis=1)[0]
        pred_prob = np.max(preds, axis=1)[0]

        angle = self.label_list[pred_idx]
        confidence = float(pred_prob)

        return [{'angle': angle, 'confidence': confidence}]

    def classify(self, image: np.ndarray) -> Dict:
        original_size = (image.shape[1], image.shape[0])
        results = self.run(image, original_size=original_size, conf_threshold=0.5)
        return results[0] if results else {'angle': '0', 'confidence': 0.0}

    def needs_rotation(self, image: np.ndarray, conf_threshold: float = 0.9) -> Tuple[bool, float]:
        """
        Check if textline needs 180° rotation

        Args:
            image: Input textline image
            conf_threshold: Confidence threshold

        Returns:
            Tuple of (needs_rotation, confidence)
        """
        result = self.classify(image)
        angle = result.get('angle', '0')
        confidence = result.get('confidence', 0.0)

        if confidence >= conf_threshold and angle == '180':
            return True, confidence
        return False, confidence
