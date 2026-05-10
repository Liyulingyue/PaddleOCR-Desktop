import base64
import io
import warnings
from typing import Any, Dict, List, Optional

import numpy as np

from .genai_client import GenAIClient, GenAIConfig, HAS_OPENAI
from .batch_sampler import DocVLMBatchSampler
from .utils.postprocess import format_vlm_result

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

PADDLEOCR_VL_MAX_NEW_TOKENS = 4096
PADDLEOCR_VL_GENAI_CLIENT_BATCH_SIZE = 8


def _require_openai():
    if not HAS_OPENAI:
        raise ImportError(
            "The 'openai' package is required for VLM inference. "
            "Install it with: pip install openai"
        )


def _apply_chat_template_text(messages: List[Dict]) -> str:
    cls_token = "<|begin_of_sentence|>"
    eos_token = "</s>"
    lines = [cls_token]
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
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


class DocVLMGenAIClientPredictor:
    def __init__(
        self,
        genai_config: GenAIConfig,
        model_name: str = "PaddleOCR-VL-1.5-0.9B",
        batch_size: int = -1,
    ):
        _require_openai()
        self.model_name = model_name
        self.genai_config = genai_config
        if batch_size == -1:
            self.batch_size = PADDLEOCR_VL_GENAI_CLIENT_BATCH_SIZE
        else:
            self.batch_size = batch_size
        self.batch_sampler = DocVLMBatchSampler(model_name, self.batch_size)
        self._client: Optional[GenAIClient] = None

    @property
    def client(self) -> GenAIClient:
        if self._client is None:
            self._client = GenAIClient(
                backend=self.genai_config.backend,
                base_url=self.genai_config.server_url,
                max_concurrency=self.genai_config.max_concurrency,
                model_name=self.model_name,
                api_key=self.genai_config.api_key,
            )
        return self._client

    def predict(self, input_data: List[Dict[str, Any]], **kwargs):
        for batch in self.batch_sampler(input_data):
            results = self.process(batch, **kwargs)
            for i, result in enumerate(results):
                yield result

    def process(
        self,
        data: List[Dict[str, Any]],
        max_new_tokens: Optional[int] = None,
        skip_special_tokens: Optional[bool] = None,
        repetition_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        min_pixels: Optional[int] = None,
        max_pixels: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        _require_openai()
        return self._genai_client_process(
            data,
            max_new_tokens=max_new_tokens,
            skip_special_tokens=skip_special_tokens,
            repetition_penalty=repetition_penalty,
            temperature=temperature,
            top_p=top_p,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

    def _genai_client_process(
        self,
        data: List[Dict],
        max_new_tokens: Optional[int],
        skip_special_tokens: Optional[bool],
        repetition_penalty: Optional[float],
        temperature: Optional[float],
        top_p: Optional[float],
        min_pixels: Optional[int],
        max_pixels: Optional[int],
    ) -> List[Dict[str, Any]]:
        client = self.client
        futures = []

        for item in data:
            image = item["image"]
            query = item.get("query", "OCR:")

            image_url = self._encode_image(image)

            if temperature is not None:
                effective_temp = temperature
            else:
                effective_temp = 0.0

            req_kwargs: Dict[str, Any] = {"temperature": effective_temp}
            if top_p is not None:
                req_kwargs["top_p"] = top_p

            req_kwargs["max_tokens"] = (
                max_new_tokens if max_new_tokens is not None else PADDLEOCR_VL_MAX_NEW_TOKENS
            )

            req_kwargs["extra_body"] = {}
            if skip_special_tokens is not None:
                req_kwargs["extra_body"]["skip_special_tokens"] = skip_special_tokens
            if repetition_penalty is not None:
                req_kwargs["extra_body"]["repetition_penalty"] = repetition_penalty

            if min_pixels is not None:
                if client.backend == "vllm-server":
                    req_kwargs["extra_body"].setdefault("mm_processor_kwargs", {})["min_pixels"] = min_pixels
                else:
                    warnings.warn(f"{client.backend} does not support `min_pixels`.")

            if max_pixels is not None:
                if client.backend == "vllm-server":
                    req_kwargs["extra_body"].setdefault("mm_processor_kwargs", {})["max_pixels"] = max_pixels
                else:
                    warnings.warn(f"{client.backend} does not support `max_pixels`.")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": query},
                    ],
                }
            ]

            future = client.create_chat_completion(
                messages,
                return_future=True,
                timeout=600,
                **req_kwargs,
            )
            futures.append(future)

        results = []
        for i, future in enumerate(futures):
            try:
                result = future.result()
                content = result.choices[0].message.content
                results.append({"result": content, "image": data[i].get("image")})
            except Exception as e:
                for f in futures:
                    if not f.done():
                        f.cancel()
                raise

        return results

    def _encode_image(self, image) -> str:
        if isinstance(image, str):
            if image.startswith("http://") or image.startswith("https://"):
                return image
            if not HAS_PIL:
                raise ImportError("PIL is required to encode local images.")
            with Image.open(image) as img:
                img = img.convert("RGB")
                with io.BytesIO() as buf:
                    img.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{b64}"

        elif isinstance(image, np.ndarray):
            if not HAS_CV2 or not HAS_PIL:
                raise ImportError("cv2 and PIL are required to encode numpy array images.")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(image)
            with io.BytesIO() as buf:
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{b64}"

        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None
