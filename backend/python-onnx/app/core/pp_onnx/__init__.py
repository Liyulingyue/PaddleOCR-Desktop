"""
PP ONNX Model Wrappers

This package contains ONNX-based implementations of PP-OCR models:
- PPOCRv5DetONNX: Text detection
- PPOCRv5RecONNX: Text recognition  
- PPOCRv5ClsONNX: Text classification
- PPDocLayoutONNX: Document layout analysis

All models inherit from ONNXModelBase and provide a consistent
preprocess/infer/postprocess interface.
"""

from .onnx_model_base import ONNXModelBase
from .pp_ocrv5cls_onnx import PPOCRv5ClsONNX
from .pp_ocrv5det_onnx import PPOCRv5DetONNX
from .pp_ocrv5rec_onnx import PPOCRv5RecONNX
from .pp_doclayout_onnx import PPDocLayoutONNX

__all__ = [
    'ONNXModelBase',
    'PPOCRv5ClsONNX',
    'PPOCRv5DetONNX', 
    'PPOCRv5RecONNX',
    'PPDocLayoutONNX'
]