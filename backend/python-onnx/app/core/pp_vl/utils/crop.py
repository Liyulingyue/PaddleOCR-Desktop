import re
from typing import List, Dict, Tuple, Any
from pathlib import Path
import base64
import io


def apply_chat_template(
    messages: List[Dict[str, Any]],
    template_name: str = "PaddleOCR-VL-1.5-0.9B",
) -> str:
    template = _CHAT_TEMPLATES.get(template_name, _CHAT_TEMPLATES["PaddleOCR-VL-1.5-0.9B"])
    return template(messages)


def _build_paddleocr_vl_15_messages(image_data: str, text_prompt: str) -> List[Dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data}},
                {"type": "text", "text": text_prompt},
            ],
        }
    ]


def _CHAT_TEMPLATE_PADDLEOCR_VL_15(messages: List[Dict]) -> str:
    cls_token = "<|begin_of_sentence|>"
    eos_token = "</s>"
    lines = [cls_token]
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, dict) and part.get("type") == "image_url":
                    text_parts.append("<|IMAGE_START|><|IMAGE_PLACEHOLDER|><|IMAGE_END|>")
            content_str = "".join(text_parts)
        else:
            content_str = str(content)

        if role == "user":
            lines.append(f"User: {content_str}\n")
        elif role == "assistant":
            lines.append(f"Assistant:\n{content_str}{eos_token}")
    lines.append("Assistant:\n")
    return "".join(lines)


_CHAT_TEMPLATES = {
    "PaddleOCR-VL-1.5-0.9B": _CHAT_TEMPLATE_PADDLEOCR_VL_15,
}


def image_to_base64_data_url(image, fmt: str = "PNG") -> str:
    if isinstance(image, np.ndarray):
        import cv2
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        from PIL import Image
        image = Image.fromarray(image)

    if isinstance(image, str):
        from PIL import Image
        with Image.open(image) as img:
            img = img.convert("RGB")
            with io.BytesIO() as buf:
                img.save(buf, format=fmt)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    elif isinstance(image, np.ndarray):
        from PIL import Image
        import cv2
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(image)
        with io.BytesIO() as buf:
            img.save(buf, format=fmt)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    elif hasattr(image, "save"):
        with io.BytesIO() as buf:
            image.save(buf, format=fmt)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    else:
        raise TypeError(f"Unsupported image type: {type(image)}")

    return f"data:image/{fmt.lower()};base64,{b64}"


def construct_img_path(label: str, bbox: List[int]) -> str:
    x1, y1, x2, y2 = bbox[:4]
    return f"{label}_{x1}_{y1}_{x2}_{y2}.png"


def gather_imgs(doc_img, boxes) -> List[Any]:
    return []


def calc_merged_wh(images):
    widths = [img.shape[1] if hasattr(img, "shape") else 0 for img in images]
    heights = [img.shape[0] if hasattr(img, "shape") else 0 for img in images]
    return max(widths) if widths else 0, sum(heights) if heights else 0


def merge_blocks(blocks: List[Dict], non_merge_labels: List[str]) -> List[Dict]:
    return blocks


def tokenize_figure_of_table(table_img, table_box, figures):
    return table_img, {}, []


def untokenize_figure_of_table(table_res_str, figure_token_map, image_path_to_obj_map):
    return table_res_str


def pre_process_for_spotting(image):
    return image


def post_process_for_spotting(input_str, w, h):
    return input_str, {"rec_polys": [], "rec_texts": []}


# stub for numpy import used by image_to_base64_data_url
import numpy as np
