from threading import Lock
from typing import Optional

from .onnx_paddleocr import ONNXPaddleOcr

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
