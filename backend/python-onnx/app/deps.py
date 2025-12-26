from threading import Lock
from typing import Optional

from .core.onnx_paddleocr import ONNXPaddleOcr

_model: Optional[ONNXPaddleOcr] = None
_lock = Lock()


def get_model() -> ONNXPaddleOcr:
    """Return a singleton ONNXPaddleOcr instance (thread-safe)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = ONNXPaddleOcr(use_angle_cls=True, use_gpu=False)
    return _model


def unload_model():
    """Unload the OCR model instance."""
    global _model
    with _lock:
        if _model is not None:
            # Attempt to release ONNX sessions if possible
            try:
                if hasattr(_model, 'text_detector') and hasattr(_model.text_detector, 'det_onnx_session'):
                    _model.text_detector.det_onnx_session = None
                if hasattr(_model, 'text_recognizer') and hasattr(_model.text_recognizer, 'rec_onnx_session'):
                    _model.text_recognizer.rec_onnx_session = None
                if hasattr(_model, 'text_classifier') and hasattr(_model.text_classifier, 'cls_onnx_session'):
                    _model.text_classifier.cls_onnx_session = None
            except Exception:
                pass  # Ignore errors during cleanup
            _model = None


def is_model_loaded() -> bool:
    """Return whether the OCR model is currently loaded."""
    return _model is not None
