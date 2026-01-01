"""
PP-OCRv5 分类器（ONNX）封装

提供与原始 `predict_cls.TextClassifier` 行为兼容的 `PPOCRv5ClsONNX` 类，
包含 `preprocess` / `infer` / `postprocess` 接口，并提供 `classify` 方法。

用法示例：
    cls = PPOCRv5ClsONNX(model_path, use_gpu=False)
    imgs_rotated, cls_res = cls.classify([img1, img2])
"""
from typing import List, Tuple, Any, Optional
import copy
import cv2
import math
import numpy as np

from .onnx_model_base import ONNXModelBase
from .cls_postprocess import ClsPostProcess
# By default `PPOCRv5ClsONNX` uses `ClsPostProcess` for decoding; a custom
# postprocess operator may be injected via the `postprocess_op` parameter.


class PPOCRv5ClsONNX(ONNXModelBase):
    def __init__(
        self,
        model_path: str,
        use_gpu: bool = False,
        gpu_id: int = 0,
        cls_image_shape: Tuple[int, int, int] = (3, 48, 192),
        label_list: Optional[List[str]] = None,
        cls_batch_num: int = 6,
        cls_thresh: float = 0.9,
        postprocess_op: Optional[ClsPostProcess] = None,
        config_path: Optional[str] = None,
    ) -> None:
        # Don't call ONNXModelBase.run in ctor (no inference here)
        super().__init__(model_path=model_path, use_gpu=use_gpu, gpu_id=gpu_id, config_path=config_path)

        self.cls_image_shape = cls_image_shape
        self.cls_batch_num = cls_batch_num
        self.cls_thresh = cls_thresh

        if label_list is None:
            self.label_list = ["0", "180"]
        else:
            self.label_list = label_list

        # Allow injection of a custom postprocess operator; default to ClsPostProcess
        if postprocess_op is not None:
            self.postprocess_op = postprocess_op
        else:
            self.postprocess_op = ClsPostProcess(label_list=self.label_list)

    def resize_norm_img(self, img: np.ndarray) -> np.ndarray:
        imgC, imgH, imgW = self.cls_image_shape
        h = img.shape[0]
        w = img.shape[1]
        ratio = w / float(h)
        if math.ceil(imgH * ratio) > imgW:
            resized_w = imgW
        else:
            resized_w = int(math.ceil(imgH * ratio))
        resized_image = cv2.resize(img, (resized_w, imgH))
        resized_image = resized_image.astype("float32")
        if imgC == 1:
            resized_image = resized_image / 255
            resized_image = resized_image[np.newaxis, :]
        else:
            resized_image = resized_image.transpose((2, 0, 1)) / 255
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:resized_w] = resized_image
        return padding_im

    def preprocess(self, img_list: List[np.ndarray]) -> dict:
        """Convert list of images to model input dict (name->ndarray)."""
        if not isinstance(img_list, list):
            img_list = [img_list]

        img_list_copy = copy.deepcopy(img_list)
        # preserve original order via indices
        width_list = [img.shape[1] / float(img.shape[0]) for img in img_list_copy]
        indices = np.argsort(np.array(width_list))

        # We'll process in batches, but return one combined batch (caller may send partial batches)
        norm_img_batch = []
        for ino in range(len(img_list_copy)):
            norm_img = self.resize_norm_img(img_list_copy[indices[ino]])
            norm_img = norm_img[np.newaxis, :]
            norm_img_batch.append(norm_img)

        if len(norm_img_batch) == 0:
            raise ValueError("No images provided to preprocess")

        norm_img_batch = np.concatenate(norm_img_batch)
        # ONNX models often expect NCHW
        # Use the first input name for image
        input_name = self.input_names[0] if len(self.input_names) > 0 else 'image'
        return {input_name: norm_img_batch}

    def postprocess(self, outputs: List[np.ndarray], *args, **kwargs) -> List[Tuple[str, float]]:
        """Decode model outputs into (label, score) tuples.

        Prefer an injected or default `self.postprocess_op` (ClsPostProcess).
        If `postprocess_op` is absent, fall back to internal decoding with optional softmax.
        """
        if not outputs:
            return []
        # Support being passed either a list of outputs or a single array
        prob_out = outputs[0] if isinstance(outputs, (list, tuple)) else outputs

        # If a postprocess operator is available (e.g., ClsPostProcess), use it
        if hasattr(self, "postprocess_op") and self.postprocess_op is not None:
            return self.postprocess_op(prob_out)

        # Fallback (same logic as before): ensure batch dim and softmax if needed
        if prob_out.ndim == 1:
            prob_out = np.expand_dims(prob_out, 0)
        row_sums = prob_out.sum(axis=1)
        if not np.allclose(row_sums, 1.0, atol=1e-3):
            exps = np.exp(prob_out - np.max(prob_out, axis=1, keepdims=True))
            prob_out = exps / exps.sum(axis=1, keepdims=True)

        pred_idxs = prob_out.argmax(axis=1)
        decode_out = []
        for i, idx in enumerate(pred_idxs):
            label = self.label_list[idx] if idx < len(self.label_list) else str(idx)
            score = float(prob_out[i, idx])
            decode_out.append((label, score))
        return decode_out

    def classify(self, img_list: List[np.ndarray]) -> Tuple[List[np.ndarray], List[Tuple[str, float]]]:
        """High level classify helper that mimics existing TextClassifier behavior.

        Returns:
            (maybe_rotated_img_list, cls_results)
        where cls_results is a list of (label, score) per image and images rotated
        by 180 degrees when label contains '180' with score > cls_thresh.
        """
        single = False
        if not isinstance(img_list, list):
            img_list = [img_list]
            single = True

        img_list = copy.deepcopy(img_list)
        img_num = len(img_list)
        width_list = [img.shape[1] / float(img.shape[0]) for img in img_list]
        indices = np.argsort(np.array(width_list))

        cls_res = [["", 0.0]] * img_num
        batch_num = self.cls_batch_num

        for beg_img_no in range(0, img_num, batch_num):
            end_img_no = min(img_num, beg_img_no + batch_num)
            norm_img_batch = []

            for ino in range(beg_img_no, end_img_no):
                norm_img = self.resize_norm_img(img_list[indices[ino]])
                norm_img = norm_img[np.newaxis, :]
                norm_img_batch.append(norm_img)

            if len(norm_img_batch) == 0:
                continue
            norm_img_batch = np.concatenate(norm_img_batch)

            input_name = self.input_names[0] if len(self.input_names) > 0 else 'image'
            input_feed = {input_name: norm_img_batch}
            outputs = self.infer(input_feed)

            prob_out = outputs[0]
            cls_result = self.postprocess([prob_out])

            for rno in range(len(cls_result)):
                label, score = cls_result[rno]
                cls_res[indices[beg_img_no + rno]] = [label, score]
                if "180" in str(label) and score > self.cls_thresh:
                    img_list[indices[beg_img_no + rno]] = cv2.rotate(
                        img_list[indices[beg_img_no + rno]], 1
                    )

        if single:
            return img_list[0], cls_res
        return img_list, cls_res


if __name__ == "__main__":
    print("PPOCRv5ClsONNX ready")
