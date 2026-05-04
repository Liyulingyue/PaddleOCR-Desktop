"""
预处理工具函数 - 为表格识别和公式识别提供统一的预处理逻辑
参考自 PaddleOCR ppocr/data/imaug/ 和 ppstructure/table/predict_structure.py
"""

import cv2
import numpy as np
from PIL import Image, ImageOps


def resize_table_image(img: np.ndarray, max_len: int = 488) -> tuple[np.ndarray, float, float]:
    """
    调整表格图像大小，保持宽高比，使得最大边等于 max_len。
    参考自 PaddleOCR ResizeTableImage 变换。

    Args:
        img: 输入图像 (H, W, C) BGR格式
        max_len: 最大边长度

    Returns:
        resized: 调整后的图像
        ratio_h: 高度缩放比
        ratio_w: 宽度缩放比
    """
    h, w = img.shape[:2]
    ratio_h = 1.0
    ratio_w = 1.0

    if max(h, w) > max_len:
        if h > w:
            new_h = max_len
            new_w = int(w * max_len / h)
        else:
            new_w = max_len
            new_h = int(h * max_len / w)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        ratio_h = new_h / h
        ratio_w = new_w / w
    else:
        resized = img.copy()

    return resized, ratio_h, ratio_w


def normalize_image(
    img: np.ndarray,
    mean: list = [0.485, 0.456, 0.406],
    std: list = [0.229, 0.224, 0.225],
    scale: float = 1.0 / 255.0
) -> np.ndarray:
    """
    归一化图像。
    参考自 PaddleOCR NormalizeImage 变换。

    Args:
        img: 输入图像 (H, W, C)
        mean: 均值
        std: 标准差
        scale: 缩放因子

    Returns:
        归一化后的图像 (H, W, C)
    """
    img = img.astype(np.float32)
    img = img * scale
    mean = np.array(mean, dtype=np.float32)
    std = np.array(std, dtype=np.float32)
    img = (img - mean) / std
    return img


def padding_table_image(img: np.ndarray, size: int = 488) -> tuple[np.ndarray, int, int]:
    """
    将图像填充到正方形 (size x size)。
    参考自 PaddleOCR PaddingTableImage 变换。

    Args:
        img: 输入图像 (H, W, C)
        size: 目标尺寸

    Returns:
        padded: 填充后的图像 (size, size, C)
        pad_h: 高度填充量
        pad_w: 宽度填充量
    """
    h, w = img.shape[:2]
    pad_h = size - h if h < size else 0
    pad_w = size - w if w < size else 0

    if pad_h > 0 or pad_w > 0:
        padded = np.zeros((size, size, img.shape[2]), dtype=img.dtype)
        padded[:h, :w, :] = img
    else:
        padded = img

    return padded, pad_h, pad_w


def to_chw_image(img: np.ndarray) -> np.ndarray:
    """
    将 HWC 格式图像转换为 CHW 格式。
    参考自 PaddleOCR ToCHWImage 变换。

    Args:
        img: 输入图像 (H, W, C)

    Returns:
        CHW 格式图像 (C, H, W)
    """
    return img.transpose(2, 0, 1)


def preprocess_table_slanet(
    img: np.ndarray,
    max_len: int = 512,
    mean: list = [0.485, 0.456, 0.406],
    std: list = [0.229, 0.224, 0.225]
) -> tuple[np.ndarray, list]:
    """
    SLANet 表格识别的完整预处理流程。
    流程: ResizeTableImage -> NormalizeImage -> PaddingTableImage -> ToCHWImage

    Args:
        img: 输入图像 BGR格式 (H, W, 3)
        max_len: 最大边长度，默认512
        mean: 归一化均值
        std: 归一化标准差

    Returns:
        tensor: 预处理后的图像 tensor (1, 3, max_len, max_len)
        shape_info: [h, w, ratio_h, ratio_w, pad_h, pad_w] 用于后处理反归一化
    """
    ori_h, ori_w = img.shape[:2]

    resized, ratio_h, ratio_w = resize_table_image(img, max_len=max_len)
    normalized = normalize_image(resized, mean=mean, std=std)
    padded, pad_h, pad_w = padding_table_image(normalized, size=max_len)
    chw = to_chw_image(padded)

    tensor = np.expand_dims(chw.astype(np.float32), axis=0)

    shape_info = [ori_h, ori_w, ratio_h, ratio_w, pad_h, pad_w]

    return tensor, shape_info


def crop_margin(img: Image.Image) -> Image.Image:
    """
    裁剪公式图像的白色边距。
    参考自 PaddleOCR UniMERNetImgDecode.crop_margin

    Args:
        img: PIL Image

    Returns:
        裁剪后的图像
    """
    data = np.array(img.convert("L"))
    data = data.astype(np.uint8)
    max_val = data.max()
    min_val = data.min()

    if max_val == min_val:
        return img

    data = (data - min_val) / (max_val - min_val) * 255
    gray = 255 * (data < 200).astype(np.uint8)
    coords = cv2.findNonZero(gray)
    if coords is None:
        return img
    a, b, w, h = cv2.boundingRect(coords)
    return img.crop((a, b, w + a, h + b))


def preprocess_formula_unimernet(
    img: np.ndarray,
    input_size: int = 384,
    random_padding: bool = False
) -> np.ndarray:
    """
    PP-FormulaNet 公式识别的完整预处理流程。
    流程: crop_margin -> resize -> pad to (input_size, input_size) -> ToGray -> Normalize

    Args:
        img: 输入图像 BGR格式 (H, W, 3)
        input_size: 输入尺寸，默认384
        random_padding: 是否随机填充（仅用于训练，推理时为False）

    Returns:
        tensor: 预处理后的图像 tensor (1, 1, input_size, input_size)
    """
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    pil_img = crop_margin(pil_img)

    if pil_img.height == 0 or pil_img.width == 0:
        raise ValueError("Image has zero dimensions after margin cropping")

    short_edge = min(pil_img.width, pil_img.height)
    if short_edge > input_size:
        scale = input_size / short_edge
        new_w = int(pil_img.width * scale)
        new_h = int(pil_img.height * scale)
        pil_img = pil_img.resize((new_w, new_h), Image.BILINEAR)

    pil_img.thumbnail((input_size, input_size), Image.BILINEAR)

    delta_width = input_size - pil_img.width
    delta_height = input_size - pil_img.height

    if random_padding:
        import random
        pad_width = random.randint(0, delta_width)
        pad_height = random.randint(0, delta_height)
    else:
        pad_width = delta_width // 2
        pad_height = delta_height // 2

    padding = (
        pad_width,
        pad_height,
        delta_width - pad_width,
        delta_height - pad_height,
    )

    pil_img = ImageOps.expand(pil_img, padding)

    gray = pil_img.convert("L")
    gray_np = np.array(gray).astype(np.float32) / 255.0

    mean = 0.7931
    std = 0.1738
    gray_np = (gray_np - mean) / std

    tensor = np.expand_dims(gray_np, axis=0)
    tensor = np.expand_dims(tensor, axis=0)

    return tensor.astype(np.float32)
