"""
PP-OCRv5 识别（ONNX）封装

实现与 `predict_rec.TextRecognizer` 行为兼容的 `PPOCRv5RecONNX` 类，
基于 `ONNXModelBase`，并复用 `rec_postprocess` 中的 CTC/Attn 解码。
"""
from typing import List, Any, Tuple, Optional
from pathlib import Path

import numpy as np
import cv2

from .onnx_model_base import ONNXModelBase
from .rec_postprocess import CTCLabelDecode, AttnLabelDecode


class PPOCRv5RecONNX(ONNXModelBase):
    def __init__(
        self,
        model_path: str,
        use_gpu: bool = False,
        gpu_id: int = 0,
        rec_algorithm: str = "CRNN",
        rec_char_type: str = "en",
        rec_char_dict_path: Optional[str] = None,
        rec_image_shape: Tuple[int, int, int] = (3, 48, 320),
        rec_batch_num: int = 6,
        use_space_char: bool = True,
        config_path: Optional[str] = None,
    ) -> None:
        super().__init__(model_path=model_path, use_gpu=use_gpu, gpu_id=gpu_id, config_path=config_path)

        self.rec_image_shape = [int(v) for v in rec_image_shape]
        self.rec_batch_num = rec_batch_num
        self.rec_algorithm = rec_algorithm
        self.rec_char_type = rec_char_type
        self.use_space_char = use_space_char

        if self.rec_algorithm == "CTC" or self.rec_char_type == "en":
            self.postprocess_op = CTCLabelDecode(character_dict_path=rec_char_dict_path, use_space_char=use_space_char)
        else:
            self.postprocess_op = AttnLabelDecode(character_dict_path=rec_char_dict_path, use_space_char=use_space_char)

    def resize_norm_img(self, img: Any) -> np.ndarray:
        imgC, imgH, imgW = self.rec_image_shape
        h, w = img.shape[0:2]
        ratio = w / float(h)
        target_w = int(np.ceil(imgH * ratio))
        if target_w > imgW:
            target_w = imgW
        resized_image = cv2.resize(img, (target_w, imgH))
        resized_image = resized_image.astype("float32")
        if imgC == 1:
            resized_image = resized_image / 255.0
            resized_image = resized_image[np.newaxis, :]
        else:
            resized_image = resized_image.transpose((2, 0, 1)) / 255.0
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:target_w] = resized_image
        return padding_im

    def preprocess(self, img_list: List[Any]) -> dict:
        """Create batched input dict for recognizer."""
        norm_img_batch = []
        for img in img_list:
            norm_img = self.resize_norm_img(img)
            norm_img = norm_img[np.newaxis, :]
            norm_img_batch.append(norm_img)

        if len(norm_img_batch) == 0:
            return {}

        norm_img_batch = np.concatenate(norm_img_batch)
        input_name = self.input_names[0] if self.input_names else "image"
        return {input_name: norm_img_batch}

    def postprocess(self, outputs: List[np.ndarray], *args, **kwargs) -> List[Tuple[str, float]]:
        if len(outputs) == 0:
            return []
        preds = outputs[0]
        result = self.postprocess_op(preds)
        return result

    def recognize(self, img_list: List[Any]) -> List[Tuple[str, float]]:
        """High level classify helper mirroring existing recognizer behavior."""
        if not isinstance(img_list, list):
            img_list = [img_list]

        if len(img_list) == 0:
            return []

        # process in batches
        res = []
        for i in range(0, len(img_list), self.rec_batch_num):
            batch = img_list[i : i + self.rec_batch_num]
            input_feed = self.preprocess(batch)
            outputs = self.infer(input_feed)
            batch_res = self.postprocess(outputs)
            res.extend(batch_res)

        return res


if __name__ == "__main__":
    print("PPOCRv5RecONNX ready")
