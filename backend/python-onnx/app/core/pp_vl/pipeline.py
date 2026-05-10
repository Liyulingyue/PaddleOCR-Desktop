import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

from .genai_client import GenAIConfig
from .vlm_predictor import DocVLMGenAIClientPredictor
from .batch_sampler import ImageBatchSampler
from .utils.postprocess import (
    crop_margin,
    filter_overlap_boxes,
    format_vlm_result,
)
from .utils.crop import merge_blocks

IMAGE_LABELS = ["image", "header_image", "footer_image"]


class PaddleOCRVLPipeline:
    DEFAULT_MIN_PIXELS = 112896
    DEFAULT_MAX_PIXELS = 1003520
    DEFAULT_MAX_NEW_TOKENS = 4096

    def __init__(
        self,
        layout_model_path: Optional[str] = None,
        genai_config: Optional[GenAIConfig] = None,
        use_gpu: bool = False,
        gpu_id: int = 0,
        layout_threshold: float = 0.5,
        layout_nms: bool = True,
        layout_unclip_ratio: float = 1.0,
        merge_layout_blocks: bool = True,
        use_doc_preprocessor: bool = False,
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False,
    ):
        self.layout_threshold = layout_threshold
        self.layout_nms = layout_nms
        self.layout_unclip_ratio = layout_unclip_ratio
        self.merge_layout_blocks = merge_layout_blocks
        self.use_doc_preprocessor = use_doc_preprocessor
        self._layout_model = None
        self._vlm_predictor = None
        self._genai_config = genai_config
        self._layout_model_path = layout_model_path
        self._use_gpu = use_gpu
        self._gpu_id = gpu_id
        self._loaded = False

    def load(self) -> bool:
        if self._loaded:
            return True
        try:
            if self._layout_model_path:
                from ..pp_onnx.pp_doclayout_onnx import PPDocLayoutONNX
                self._layout_model = PPDocLayoutONNX(
                    model_path=self._layout_model_path,
                    use_gpu=self._use_gpu,
                    gpu_id=self._gpu_id,
                )
            if self._genai_config:
                self._vlm_predictor = DocVLMGenAIClientPredictor(
                    genai_config=self._genai_config,
                    model_name="PaddleOCR-VL-1.5-0.9B",
                    batch_size=-1,
                )
            self._loaded = True
            return True
        except Exception as e:
            print(f"Failed to load pipeline: {e}")
            return False

    def unload(self) -> bool:
        if self._vlm_predictor:
            self._vlm_predictor.close()
            self._vlm_predictor = None
        self._layout_model = None
        self._loaded = False
        return True

    def is_loaded(self) -> bool:
        return self._loaded

    def predict(
        self,
        input_data: Union[str, np.ndarray, List[str], List[np.ndarray]],
        use_layout_detection: bool = True,
        layout_threshold: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        min_pixels: Optional[int] = None,
        max_pixels: Optional[int] = None,
        **kwargs,
    ):
        if isinstance(input_data, (str, np.ndarray)):
            input_data = [input_data]

        for item in input_data:
            yield self._predict_single(
                item,
                use_layout_detection=use_layout_detection,
                layout_threshold=layout_threshold,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                min_pixels=min_pixels,
                max_pixels=max_pixels,
            )

    def _predict_single(
        self,
        image: Union[str, np.ndarray],
        use_layout_detection: bool,
        layout_threshold: Optional[float],
        max_new_tokens: Optional[int],
        temperature: Optional[float],
        top_p: Optional[float],
        repetition_penalty: Optional[float],
        min_pixels: Optional[int],
        max_pixels: Optional[int],
    ) -> Dict[str, Any]:
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not load image from {image}")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif isinstance(image, np.ndarray):
            if image.shape[2] == 3 and image.dtype == np.uint8:
                if self._is_bgr(image):
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        original_h, original_w = image.shape[:2]

        if use_layout_detection and self._layout_model is not None:
            thresh = layout_threshold if layout_threshold is not None else self.layout_threshold
            regions = self._layout_model.detect(image, conf_threshold=thresh)
        else:
            regions = [
                {
                    "bbox": [0, 0, original_w, original_h],
                    "type": "text",
                    "confidence": 1.0,
                }
            ]

        blocks = self._crop_and_merge_blocks(image, regions)

        if self._vlm_predictor is None:
            return {
                "input_path": None,
                "width": original_w,
                "height": original_h,
                "layout_det_res": {"boxes": [self._region_to_box(r) for r in regions]},
                "parsing_res_list": [
                    {"label": b["label"], "bbox": b["box"], "content": ""}
                    for b in blocks
                ],
            }

        vlm_kwargs = {
            "max_new_tokens": max_new_tokens if max_new_tokens is not None else self.DEFAULT_MAX_NEW_TOKENS,
            "temperature": temperature if temperature is not None else 0.0,
            "skip_special_tokens": True,
        }
        if top_p is not None:
            vlm_kwargs["top_p"] = top_p
        if repetition_penalty is not None:
            vlm_kwargs["repetition_penalty"] = repetition_penalty

        parsing_res_list = self._vlm_inference(blocks, vlm_kwargs, min_pixels, max_pixels)

        return {
            "input_path": None,
            "width": original_w,
            "height": original_h,
            "layout_det_res": {"boxes": [self._region_to_box(r) for r in regions]},
            "parsing_res_list": parsing_res_list,
        }

    def _is_bgr(self, image: np.ndarray) -> bool:
        import numpy as np
        top_left = image[0, 0]
        if image.shape[2] == 3:
            r, g, b = int(top_left[0]), int(top_left[1]), int(top_left[2])
            if r > g and r > b:
                return True
        return False

    def _region_to_box(self, region: Dict) -> Dict:
        bbox = region.get("bbox", [0, 0, 0, 0])
        return {
            "label": region.get("type", "text"),
            "coordinate": bbox,
            "score": region.get("confidence", 1.0),
            "polygon_points": [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
            ] if len(bbox) >= 4 else None,
        }

    def _crop_and_merge_blocks(
        self,
        image: np.ndarray,
        regions: List[Dict],
    ) -> List[Dict]:
        h, w = image.shape[:2]
        boxes = []
        for region in regions:
            bbox = region.get("bbox", [])
            if len(bbox) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            cropped = image[y1:y2, x1:x2]
            boxes.append({
                "box": [x1, y1, x2, y2],
                "label": region.get("type", "text"),
                "img": cropped,
                "coordinate": [x1, y1, x2, y2],
            })

        if self.merge_layout_blocks:
            image_labels = IMAGE_LABELS + ["seal", "chart"]
            boxes = merge_blocks(boxes, non_merge_labels=image_labels + ["table"])

        return boxes

    def _vlm_inference(
        self,
        blocks: List[Dict],
        vlm_kwargs: Dict,
        min_pixels: Optional[int],
        max_pixels: Optional[int],
    ) -> List[Dict]:
        batch_dict_by_pixel: Dict[Tuple, Dict] = {}
        id2pixel_key: Dict[int, Tuple] = {}

        for j, block in enumerate(blocks):
            block_img = block.get("img")
            block_label = block.get("label", "text")
            if block_img is None:
                continue

            if block_label in IMAGE_LABELS or block_label == "seal" or block_label == "chart":
                continue

            if block_label == "table":
                text_prompt = "Table Recognition:"
            elif block_label == "formula" or "formula" in block_label:
                text_prompt = "Formula Recognition:"
                cropped = crop_margin(block_img)
                if cropped.shape[0] > 2 and cropped.shape[1] > 2:
                    block_img = cropped
            else:
                text_prompt = "OCR:"

            mp = min_pixels if min_pixels is not None else self.DEFAULT_MIN_PIXELS
            mxp = max_pixels if max_pixels is not None else self.DEFAULT_MAX_PIXELS
            pixel_key = (mp, mxp)

            if pixel_key not in batch_dict_by_pixel:
                batch_dict_by_pixel[pixel_key] = {
                    "images": [],
                    "queries": [],
                    "block_ids": [],
                }
            batch_dict_by_pixel[pixel_key]["images"].append(block_img)
            batch_dict_by_pixel[pixel_key]["queries"].append(text_prompt)
            batch_dict_by_pixel[pixel_key]["block_ids"].append(j)
            id2pixel_key[j] = pixel_key

        block_results: Dict[int, str] = {}
        for pixel_key, batch_info in batch_dict_by_pixel.items():
            mp, mxp = pixel_key
            kwargs = {**vlm_kwargs, "min_pixels": mp, "max_pixels": mxp}
            batch_data = [
                {"image": img, "query": q}
                for img, q in zip(batch_info["images"], batch_info["queries"])
            ]
            try:
                results = list(self._vlm_predictor.predict(batch_data, **kwargs))
                for i, result in enumerate(results):
                    block_idx = batch_info["block_ids"][i]
                    block_label = blocks[block_idx].get("label", "text")
                    result_str = result.get("result", "")
                    result_str = format_vlm_result(result_str, block_label)
                    block_results[block_idx] = result_str
            except Exception as e:
                print(f"VLM inference error: {e}")
                for i in range(len(batch_info["block_ids"])):
                    block_results[batch_info["block_ids"][i]] = ""

        parsing_res = []
        for j, block in enumerate(blocks):
            content = block_results.get(j, "")
            parsing_res.append({
                "label": block.get("label", "text"),
                "bbox": block.get("box", []),
                "content": content,
                "polygon_points": [
                    [block["box"][0], block["box"][1]],
                    [block["box"][2], block["box"][1]],
                    [block["box"][2], block["box"][3]],
                    [block["box"][0], block["box"][3]],
                ] if len(block.get("box", [])) >= 4 else None,
            })
        return parsing_res

    def result_to_markdown(self, result: Dict[str, Any]) -> Dict[str, Any]:
        parsing_list = result.get("parsing_res_list", [])
        lines = []
        images = []
        for block in parsing_list:
            label = block.get("label", "")
            content = block.get("content", "")
            bbox = block.get("bbox", [])

            if label == "text" or label == "paragraph" or label == "content":
                lines.append(content)
                lines.append("")
            elif label == "table":
                lines.append(content)
                lines.append("")
            elif label in IMAGE_LABELS or label == "chart":
                img_data = block.get("image")
                if img_data is not None:
                    img_path = f"images/{label}_{bbox[0]}_{bbox[1]}.png"
                    images.append({"filename": img_path, "data": img_data})
                    lines.append(f"![{label}]({img_path})")
                    lines.append("")
                else:
                    lines.append(f"![{label}]")
                    lines.append("")
            elif "formula" in label:
                lines.append(content)
                lines.append("")
            else:
                if content:
                    lines.append(content)
                    lines.append("")

        return {
            "markdown": "\n".join(lines),
            "images": images,
        }
