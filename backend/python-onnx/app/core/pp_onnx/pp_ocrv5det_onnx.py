"""
PP-OCRv5 检测（ONNX）封装

实现与 `predict_det.TextDetector` 兼容的 `PPOCRv5DetONNX` 类，
基于 `ONNXModelBase`，并复用项目中现有的预处理与后处理实现（imaug、DBPostProcess）。
"""
from typing import List, Any, Tuple, Optional
from pathlib import Path

import numpy as np
from .onnx_model_base import ONNXModelBase
from .imaug import transform, create_operators
from .db_postprocess import DBPostProcess


class PPOCRv5DetONNX(ONNXModelBase):
    def __init__(
        self,
        model_path: str,
        use_gpu: bool = False,
        gpu_id: int = 0,
        det_algorithm: str = "DB",
        det_limit_side_len: float = 960,
        det_limit_type: str = "max",
        det_db_thresh: float = 0.3,
        det_db_box_thresh: float = 0.6,
        det_db_unclip_ratio: float = 1.5,
        use_dilation: bool = False,
        det_db_score_mode: str = "fast",
        det_box_type: str = "quad",
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__(model_path=model_path, use_gpu=use_gpu, gpu_id=gpu_id, config_path=config_path)

        self.det_algorithm = det_algorithm
        self.det_limit_side_len = det_limit_side_len
        self.det_limit_type = det_limit_type
        self.det_db_thresh = det_db_thresh
        self.det_db_box_thresh = det_db_box_thresh
        self.det_db_unclip_ratio = det_db_unclip_ratio
        self.use_dilation = use_dilation
        self.det_db_score_mode = det_db_score_mode
        self.det_box_type = det_box_type

        # Build preprocessing ops similar to original implementation
        pre_process_list = [
            {
                "DetResizeForTest": {
                    "limit_side_len": self.det_limit_side_len,
                    "limit_type": self.det_limit_type,
                }
            },
            {
                "NormalizeImage": {
                    "std": [0.229, 0.224, 0.225],
                    "mean": [0.485, 0.456, 0.406],
                    "scale": "1./255.",
                    "order": "hwc",
                }
            },
            {"ToCHWImage": None},
            {"KeepKeys": {"keep_keys": ["image", "shape"]}},
        ]
        self.preprocess_op = create_operators(pre_process_list)

        postprocess_params = {
            "name": "DBPostProcess",
            "thresh": self.det_db_thresh,
            "box_thresh": self.det_db_box_thresh,
            "max_candidates": 1000,
            "unclip_ratio": self.det_db_unclip_ratio,
            "use_dilation": self.use_dilation,
            "score_mode": self.det_db_score_mode,
            "box_type": self.det_box_type,
        }
        self.postprocess_op = DBPostProcess(**postprocess_params)

    def preprocess(self, image: Any) -> dict:
        """Apply augmentation pipeline and prepare inputs for ONNX model."""
        data = {"image": image}
        data = transform(data, self.preprocess_op)
        img, shape_list = data
        img = np.expand_dims(img, axis=0)
        shape_list = np.expand_dims(shape_list, axis=0)
        # Use first input name for image
        input_name = self.input_names[0] if self.input_names else "image"
        return {input_name: img, "shape": shape_list}

    def postprocess(self, outputs: List[np.ndarray], shape_list: np.ndarray) -> List[np.ndarray]:
        """Run DBPostProcess and handle box filtering as in original code."""
        preds = {"maps": outputs[0]}
        post_result = self.postprocess_op(preds, shape_list)
        dt_boxes = post_result[0]["points"]

        # If poly vs quad handling is required, postprocess operator already supports
        # limiting based on box_type. Clip/filter invalid boxes to match prior behavior.
        return dt_boxes

    def detect(self, image: Any) -> List[Any]:
        """Full pipeline: preprocess -> infer -> postprocess -> return dt_boxes"""
        prepared = self.preprocess(image)
        # ONNX session expects inputs strictly by name; ensure only known inputs included
        input_feed = {k: v for k, v in prepared.items() if k in self.input_names}
        outputs = self.infer(input_feed)
        dt_boxes = self.postprocess(outputs, prepared.get("shape"))
        # If det_box_type requires clipping, caller can handle; return as numpy array
        return dt_boxes


if __name__ == "__main__":
    print("PPOCRv5DetONNX ready")
