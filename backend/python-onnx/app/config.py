"""
PaddleOCR Desktop 配置文件

此文件包含两类配置：
1. MODEL_REGISTRY: 模型名称到下载源的映射关系
2. PIPELINE_CONFIG: pipeline和使用模型的对应关系

使用示例：
    # 获取pipeline使用的所有模型
    models = get_pipeline_models("pp_structure_v3")

    # 获取单个模型路径
    layout_path = get_model_path_from_registry("PP-DocLayout-L-ONNX")
"""

import os
from pathlib import Path
import requests
from typing import Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MODELS_DIR = os.path.join(BASE_DIR, "models")

def get_models_dir():
    return os.environ.get("PPOCR_MODELS_DIR", DEFAULT_MODELS_DIR)

# =============================================================================
# 模型注册表：模型名称到下载源的映射
# =============================================================================
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # PP-StructureV3 相关模型
    "PP-DocLayout-L-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-L-ONNX",  # 魔搭社区模型ID
    },
    "PP-DocLayout-M-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-M-ONNX",  # 魔搭社区模型ID
    },
    "PP-DocLayout-S-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-S-ONNX",  # 魔搭社区模型ID
    },
    "PP-DocLayout-plus-L-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-plus-L-ONNX",  # 魔搭社区模型ID
    },
}

# =============================================================================
# Pipeline配置：pipeline和使用模型的对应关系
# =============================================================================
PIPELINE_CONFIG: Dict[str, Dict[str, Any]] = {
    "pp_structure_v3": {
        "models": {
            "layout": "PP-DocLayout-L-ONNX",
            "ocr_det": "PP-OCRv5-Det",
            "ocr_rec": "PP-OCRv5-Rec",
            "ocr_cls": "PP-OCRv5-Cls",
            "ocr_dict": "PP-OCRv5-Dict"
        },
        "description": "PP-StructureV3 完整文档结构分析流水线"
    },
    "ppocrv5": {
        "models": {
            "det": "PP-OCRv5-Det",
            "rec": "PP-OCRv5-Rec",
            "cls": "PP-OCRv5-Cls",
            "dict": "PP-OCRv5-Dict"
        },
        "description": "PP-OCRv5 OCR识别流水线"
    }
}

# 向后兼容的旧配置（已废弃，建议使用新的结构）
models_config = {
    "pp_structure_v3": {
        "layout": MODEL_REGISTRY["PP-DocLayout-L-ONNX"],
        "ocr_det": MODEL_REGISTRY["PP-OCRv5-Det"],
        "ocr_rec": MODEL_REGISTRY["PP-OCRv5-Rec"],
        "ocr_cls": MODEL_REGISTRY["PP-OCRv5-Cls"],
        "ocr_dict": MODEL_REGISTRY["PP-OCRv5-Dict"]
    },
    "ppocrv5": {
        "det": MODEL_REGISTRY["PP-OCRv5-Det"],
        "rec": MODEL_REGISTRY["PP-OCRv5-Rec"],
        "cls": MODEL_REGISTRY["PP-OCRv5-Cls"],
        "dict": MODEL_REGISTRY["PP-OCRv5-Dict"]
    }
}

def get_model_path(model_type: str, component: str) -> Optional[str]:
    """
    获取模型路径，如果本地不存在则尝试下载

    Args:
        model_type: 模型类型，如 'pp_structure_v3'
        component: 组件名称，如 'layout', 'ocr_det'

    Returns:
        模型文件路径，如果失败返回None
    """
    if model_type not in models_config or component not in models_config[model_type]:
        return None

    config = models_config[model_type][component]
    models_dir = Path(get_models_dir())
    local_path = models_dir / config["local_path"]

    if local_path.exists():
        return str(local_path)

    # 如果不存在，尝试下载
    if download_model(config, models_dir):
        return str(local_path)

    return None

def get_pipeline_models(pipeline_name: str) -> Dict[str, str]:
    """
    获取pipeline使用的模型列表

    Args:
        pipeline_name: pipeline名称，如 'pp_structure_v3'

    Returns:
        模型名称到路径的映射字典
    """
    if pipeline_name not in PIPELINE_CONFIG:
        return {}

    pipeline_config = PIPELINE_CONFIG[pipeline_name]
    models = {}

    for component, model_name in pipeline_config["models"].items():
        path = get_model_path_from_registry(model_name)
        if path:
            models[component] = path

    return models

def get_model_path_from_registry(model_name: str) -> Optional[str]:
    """
    从模型注册表获取模型路径

    Args:
        model_name: 模型名称，如 'PP-DocLayout-L-ONNX'

    Returns:
        模型文件路径，如果失败返回None
    """
    if model_name not in MODEL_REGISTRY:
        return None

    config = MODEL_REGISTRY[model_name]
    models_dir = Path(get_models_dir())
    local_path = models_dir / config["local_path"]

    if local_path.exists():
        return str(local_path)

    # 如果不存在，尝试下载
    if download_model(config, models_dir):
        return str(local_path)

    return None

def download_model(config: Dict[str, Any], models_dir: Path) -> bool:
    """
    下载模型文件

    Args:
        config: 模型配置
        models_dir: 模型目录

    Returns:
        下载是否成功
    """
    try:
        local_path = models_dir / config["local_path"]
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 优先使用ModelScope下载
        if "modelscope_id" in config:
            try:
                from modelscope import snapshot_download
                print(f"Downloading from ModelScope: {config['modelscope_id']}...")
                # 下载到临时目录
                temp_dir = snapshot_download(config["modelscope_id"], cache_dir=str(models_dir.parent / "temp"))
                temp_model_path = Path(temp_dir) / "inference.onnx"  # 假设模型文件名为inference.onnx

                if temp_model_path.exists():
                    # 复制到目标位置
                    import shutil
                    shutil.copy2(temp_model_path, local_path)
                    print(f"Successfully downloaded from ModelScope: {config['modelscope_id']}")
                    return True
                else:
                    print(f"Model file not found in ModelScope download: {temp_model_path}")
            except ImportError:
                print("modelscope library not installed, falling back to HTTP download")
            except Exception as e:
                print(f"ModelScope download failed: {e}, falling back to HTTP download")

        # HTTP下载作为fallback
        if config.get("is_tar", False):
            # 下载tar文件并解压
            import tarfile
            import tempfile

            temp_tar = local_path.with_suffix('.tar')
            print(f"Downloading {config['remote_url']}...")
            response = requests.get(config["remote_url"], timeout=300)
            response.raise_for_status()

            with open(temp_tar, 'wb') as f:
                f.write(response.content)

            # 解压到指定目录
            extract_path = models_dir / config.get("extract_path", local_path.parent)
            extract_path.mkdir(parents=True, exist_ok=True)

            with tarfile.open(temp_tar, 'r') as tar:
                tar.extractall(extract_path)

            temp_tar.unlink()  # 删除临时tar文件
            print(f"Successfully downloaded and extracted {config['remote_url']}")
        else:
            # 直接下载文件
            print(f"Downloading {config['remote_url']}...")
            response = requests.get(config["remote_url"], timeout=30)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            print(f"Successfully downloaded {config['remote_url']}")

        return True
    except Exception as e:
        print(f"Failed to download model: {e}")
        return False