"""
ONNXModelBase

A lightweight base class for ONNX models that provides a standard
preprocess/infer/postprocess interface and convenience helpers for
loading sessions and input/output names. Inherits from existing
PredictBase to reuse session and I/O utilities.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import numpy as np

import onnxruntime


class ONNXModelBase(object):
    """Standalone ONNX model base (no dependency on PredictBase).

    Provides equivalent helpers to the previous `PredictBase`:
      - get_onnx_session
      - get_output_name
      - get_input_name
      - get_input_feed

    This keeps `ONNXModelBase` self-contained so it can be used without
    relying on the older helper class.
    """

    def get_onnx_session(self, model_dir, use_gpu, gpu_id = 0):
        if use_gpu:
            providers =[('CUDAExecutionProvider',{"cudnn_conv_algo_search": "DEFAULT","device_id": gpu_id}),'CPUExecutionProvider']
        else:
            providers =['CPUExecutionProvider']

        onnx_session = onnxruntime.InferenceSession(model_dir, None, providers=providers)
        return onnx_session

    def get_output_name(self, onnx_session):
        output_name = []
        for node in onnx_session.get_outputs():
            output_name.append(node.name)
        return output_name

    def get_input_name(self, onnx_session):
        input_name = []
        for node in onnx_session.get_inputs():
            input_name.append(node.name)
        return input_name

    def get_input_feed(self, input_name, image_numpy):
        input_feed = {}
        for name in input_name:
            input_feed[name] = image_numpy
        return input_feed
    """Base wrapper for ONNX models.

    Subclasses should implement `preprocess` and `postprocess` methods.
    ``run`` orchestrates preprocess -> infer -> postprocess.
    """

    def __init__(
        self,
        model_path: str,
        use_gpu: bool = False,
        gpu_id: int = 0,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.model_path = Path(model_path)
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.config = None

        if config_path:
            cfg_path = Path(config_path)
            if cfg_path.exists():
                with cfg_path.open("r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)

        # Create ONNX session using PredictBase helper
        self.session = self.get_onnx_session(str(self.model_path), self.use_gpu, gpu_id=self.gpu_id)
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.output_names = [o.name for o in self.session.get_outputs()]
        self.input_shapes = [i.shape for i in self.session.get_inputs()]

    def preprocess(self, *args, **kwargs) -> Dict[str, np.ndarray]:
        """Convert inputs to a dict mapping input names to numpy arrays.

        Subclasses must override this method and return a dict compatible
        with :meth:`infer` input_feed. Example:
            return { 'image': batch_input }
        """
        raise NotImplementedError("preprocess must be implemented by subclass")

    def postprocess(self, outputs: List[np.ndarray], *args, **kwargs) -> Any:
        """Convert raw model outputs into user-facing results.

        Subclasses must override this method.
        """
        raise NotImplementedError("postprocess must be implemented by subclass")

    def infer(self, input_feed: Dict[str, np.ndarray]) -> List[np.ndarray]:
        """Run ONNX inference and return raw outputs."""
        # Ensure input keys exist in model inputs
        # ONNX Runtime accepts a dict of name->ndarray
        outputs = self.session.run(self.output_names, input_feed=input_feed)
        return outputs

    def run(self, *args, **kwargs) -> Any:
        """High-level API: preprocess -> infer -> postprocess."""
        input_feed = self.preprocess(*args, **kwargs)
        if not isinstance(input_feed, dict):
            raise ValueError("preprocess must return a dict mapping input names to numpy arrays")
        outputs = self.infer(input_feed)
        return self.postprocess(outputs, *args, **kwargs)


if __name__ == "__main__":
    print("ONNXModelBase ready")
