"""
UVDoc 文档图像纠偏 ONNX 推理实现

功能: 将弯曲/透视变形的文档图像纠正为正视图像

模型: DocUNet (UVDoc)
输入: (batch, 3, H, W) BGR图像归一化到[0,1]
输出: (batch, 3, H, W) 纠正后的图像，归一化到[0,1]
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Union, Tuple

from .onnx_model_base import ONNXModelBase


class UVDocONNX(ONNXModelBase):
    """
    UVDoc 文档图像纠偏 ONNX 推理类

    支持动态输入尺寸，适用于各种分辨率的文档图像。
    """

    def __init__(
        self,
        model_path: str = None,
        use_gpu: bool = False,
        gpu_id: int = 0
    ):
        if model_path is None:
            from ...config import get_model_path_from_registry
            model_dir = get_model_path_from_registry("UVDoc-ONNX")
            if model_dir is None:
                raise FileNotFoundError("UVDoc-ONNX model not found in registry")
            model_path = model_dir

        model_dir = Path(model_path)
        onnx_file = model_dir / "inference.onnx"
        if not onnx_file.exists():
            raise FileNotFoundError(f"ONNX model not found at {onnx_file}")

        super().__init__(str(onnx_file), use_gpu=use_gpu, gpu_id=gpu_id)

    def preprocess(self, img: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        预处理文档图像

        流程 (参考 C++ 实现):
        1. BGR -> 归一化到 [0, 1] (除以 255)
        2. HWC -> CHW
        3. 添加 batch 维度
        """
        h, w = img.shape[:2]

        normalized = img.astype(np.float32) / 255.0
        chw = normalized.transpose(2, 0, 1)
        batched = np.expand_dims(chw, axis=0)

        info = {
            "original_shape": img.shape,
            "height": h,
            "width": w,
        }

        return batched.astype(np.float32), info

    def postprocess(self, output: np.ndarray) -> np.ndarray:
        """
        后处理模型输出

        流程 (参考 C++ 实现 DocTrPostProcess):
        1. 移除 batch 维度 -> (3, H, W)
        2. 乘以 255 恢复到 [0, 255]
        3. CHW -> HWC
        4. 转换为 uint8
        """
        if output.shape[0] == 1:
            output = output[0]

        restored = output * 255.0
        restored = np.clip(restored, 0, 255).astype(np.uint8)
        hwc = restored.transpose(1, 2, 0)

        return hwc

    def unwarp(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        文档图像纠偏

        Args:
            img: BGR 图像 (H, W, 3) uint8

        Returns:
            unwarped: 纠偏后的 BGR 图像 uint8
            elapsed_time: 推理耗时（秒）
        """
        import time
        start_time = time.time()

        tensor, info = self.preprocess(img)

        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name

        outputs = self.session.run(
            [output_name],
            {input_name: tensor}
        )

        unwarped = self.postprocess(outputs[0])
        elapsed_time = time.time() - start_time

        return unwarped, elapsed_time

    def __call__(self, img: np.ndarray) -> np.ndarray:
        unwarped, _ = self.unwarp(img)
        return unwarped
