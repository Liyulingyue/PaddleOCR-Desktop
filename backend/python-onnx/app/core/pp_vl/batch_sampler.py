import math
from typing import List, Dict, Any


class DocVLMBatchSampler:
    DEFAULT_BATCH_SIZE = 8

    def __init__(self, model_name: str = "PaddleOCR-VL-1.5-0.9B", batch_size: int = -1):
        self.model_name = model_name
        if batch_size == -1:
            self.batch_size = self.DEFAULT_BATCH_SIZE
        else:
            self.batch_size = batch_size

    def __call__(self, input_data: List[Dict[str, Any]]):
        for i in range(0, len(input_data), self.batch_size):
            yield input_data[i : i + self.batch_size]


class ImageBatchSampler:
    def __init__(self, batch_size: int = 1):
        self.batch_size = batch_size

    def __call__(self, input_data: List):
        for i in range(0, len(input_data), self.batch_size):
            yield input_data[i : i + self.batch_size]
