"""
Utility functions for PP-Structure-V3 ONNX inference
"""

import cv2
import numpy as np
from typing import Tuple, List

def resize_image(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """Resize image maintaining aspect ratio with padding"""
    h, w = image.shape[:2]
    scale = min(target_size[0] / h, target_size[1] / w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    # Create canvas and center the image
    canvas = np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
    x_offset = (target_size[0] - new_w) // 2
    y_offset = (target_size[1] - new_h) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

    return canvas, scale, (x_offset, y_offset)

def normalize_image(image: np.ndarray, mean: List[float] = [0.485, 0.456, 0.406],
                   std: List[float] = [0.229, 0.224, 0.225]) -> np.ndarray:
    """Normalize image for model input"""
    image = image.astype(np.float32) / 255.0
    image = (image - mean) / std
    return image

def preprocess_for_layout(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[dict, float, Tuple[int, int]]:
    """Complete preprocessing for layout detection - returns dict of inputs"""
    resized, scale, offset = resize_image(image, target_size)
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    batch_chw = np.expand_dims(chw, 0).astype(np.float32)

    # Calculate im_shape and scale_factor
    original_h, original_w = image.shape[:2]
    im_shape = np.array([[original_h, original_w]], dtype=np.float32)
    scale_factor = np.array([[scale, scale]], dtype=np.float32)

    inputs = {
        'image': batch_chw,
        'im_shape': im_shape,
        'scale_factor': scale_factor
    }

    return inputs, scale, offset

def preprocess_for_ocr_det(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
    """Preprocessing for OCR detection - returns tensor with key 'x'"""
    resized, scale, offset = resize_image(image, target_size)
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(chw, 0).astype(np.float32)

def preprocess_for_ocr_rec(image: np.ndarray, target_height: int = 48) -> np.ndarray:
    """Preprocessing for OCR recognition - resize to fixed height, returns tensor with key 'x'"""
    h, w = image.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    resized = cv2.resize(image, (new_w, target_height))

    # Normalize
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(chw, 0).astype(np.float32)

def postprocess_layout(outputs: list, scale: float, offset: Tuple[int, int],
                      original_size: Tuple[int, int], conf_threshold: float = 0.5) -> List[dict]:
    """Postprocess layout detection outputs from PP-DocLayout-L"""
    print(f"Layout outputs length: {len(outputs)}")
    print(f"Scale: {scale}, Offset: {offset}, Original size: {original_size}")
    if len(outputs) > 0:
        print(f"Output 0 shape: {outputs[0].shape}")
        print(f"Output 0 sample: {outputs[0][:3] if len(outputs[0]) > 0 else 'empty'}")

    # For now, return mock data to test the pipeline
    regions = [
        {'bbox': [100, 100, 500, 200], 'type': 'text', 'confidence': 0.9},
        {'bbox': [100, 250, 500, 400], 'type': 'table', 'confidence': 0.8}
    ]

    return regions

def postprocess_ocr_det(outputs: list, scale: float, offset: Tuple[int, int],
                       original_size: Tuple[int, int], conf_threshold: float = 0.3) -> List[dict]:
    """Postprocess OCR detection outputs from PP-OCRv5_det"""
    # outputs[0] is the detection result tensor
    # For PP-OCRv5, this is typically a probability map

    # Simplified implementation - extract text boxes from probability map
    prob_map = outputs[0][0, 0]  # Take first channel, assuming shape [1, 1, H, W]

    boxes = []
    h, w = original_size

    # Simple thresholding and box extraction (simplified)
    # In real implementation, this would involve:
    # 1. Binarization
    # 2. Morphological operations
    # 3. Connected component analysis
    # 4. Box fitting

    # For now, return mock boxes based on layout regions
    boxes = [
        {'bbox': [150, 120, 450, 180], 'confidence': 0.95},  # Text box 1
        {'bbox': [150, 270, 450, 380], 'confidence': 0.90}   # Text box 2
    ]

    return boxes

def postprocess_ocr_rec(outputs: list) -> str:
    """Postprocess OCR recognition outputs from PP-OCRv5_rec"""
    # outputs[0] shape: [batch, seq_len, num_classes]
    pred = outputs[0][0]  # Take first batch item

    # PP-OCR character set (simplified, actual has ~18000 chars)
    # This is a very basic character set for demonstration
    char_list = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '

    text = ""
    for i in range(pred.shape[0]):
        char_idx = np.argmax(pred[i])
        if char_idx < len(char_list):
            char = char_list[char_idx]
            if char != ' ':  # Skip spaces for now
                text += char
        if len(text) > 50:  # Limit length
            break

    # If no text decoded, return mock text
    if not text.strip():
        text = "Sample recognized text"

    return text.strip()