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
import sys
from pathlib import Path
import requests
from typing import Dict, Any, Optional

def _resolve_base_dir() -> str:
    # Prefer the executable directory when bundled (PyInstaller, etc.)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = _resolve_base_dir()
DEFAULT_MODELS_DIR = os.path.join(BASE_DIR, "models")

def get_models_dir():
    models_dir = os.environ.get("PPOCR_MODELS_DIR", DEFAULT_MODELS_DIR)
    # 确保目录存在
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    return models_dir

def get_work_dir():
    """获取工作目录（比models目录高一级，通常是项目根目录）"""
    return BASE_DIR

# =============================================================================
# 模型注册表：模型名称到下载源的映射
# =============================================================================
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 文档结构模型（ModelScope）
    "PP-DocLayout-L-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-L-ONNX",
        "local_path": "models/PP-DocLayout-L-ONNX",
    },
    "PP-DocLayout-M-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-M-ONNX",
        "local_path": "models/PP-DocLayout-M-ONNX",
    },
    "PP-DocLayout-S-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout-S-ONNX",
        "local_path": "models/PP-DocLayout-S-ONNX",
    },
    "PP-DocLayout_plus-L-ONNX": {
        "modelscope_id": "Liyulingyue/PP-DocLayout_plus-L-ONNX",
        "local_path": "models/PP-DocLayout_plus-L-ONNX",
    },

    # PP-OCRv5 系列（移动/服务器版本）
    "PP-OCRv5_mobile_det-ONNX": {
        "modelscope_id": "Liyulingyue/PP-OCRv5_mobile_det-ONNX",
        "local_path": "models/PP-OCRv5_mobile_det-ONNX",
    },
    "PP-OCRv5_mobile_rec-ONNX": {
        "modelscope_id": "Liyulingyue/PP-OCRv5_mobile_rec-ONNX",
        "local_path": "models/PP-OCRv5_mobile_rec-ONNX",
    },
    "PP-OCRv5_server_det-ONNX": {
        "modelscope_id": "Liyulingyue/PP-OCRv5_server_det-ONNX",
        "local_path": "models/PP-OCRv5_server_det-ONNX",
    },
    "PP-OCRv5_server_rec-ONNX": {
        "modelscope_id": "Liyulingyue/PP-OCRv5_server_rec-ONNX",
        "local_path": "models/PP-OCRv5_server_rec-ONNX",
    },

    "PP-LCNet_x1_0_textline_ori-ONNX": {
        "modelscope_id": "Liyulingyue/PP-LCNet_x1_0_textline_ori-ONNX",
        "local_path": "models/PP-LCNet_x1_0_textline_ori-ONNX",
    },
    "PP-LCNet_x0_25_textline_ori-ONNX": {
        "modelscope_id": "Liyulingyue/PP-LCNet_x0_25_textline_ori-ONNX",
        "local_path": "models/PP-LCNet_x0_25_textline_ori-ONNX",
    },
    "PP-LCNet_x1_0_doc_ori-ONNX": {
        "modelscope_id": "Liyulingyue/PP-LCNet_x1_0_doc_ori-ONNX",
        "local_path": "models/PP-LCNet_x1_0_doc_ori-ONNX",
    },

    "UVDoc-ONNX": {
        "modelscope_id": "Liyulingyue/UVDoc-ONNX",
        "local_path": "models/UVDoc-ONNX",
    },
}

PIPELINE_CONFIG: Dict[str, Dict[str, Any]] = {
    "pp_structure_v3": {
        "models": {
            "layout_det": "PP-DocLayout-L-ONNX",
            "ocr_det": "PP-OCRv5_mobile_det-ONNX",
            "ocr_rec": "PP-OCRv5_mobile_rec-ONNX",
            "doc_cls": "PP-LCNet_x1_0_textline_ori-ONNX",
        },
    },
    "ppocrv5": {
        "models": {
            "ocr_det": "PP-OCRv5_mobile_det-ONNX",
            "ocr_rec": "PP-OCRv5_mobile_rec-ONNX",
            "doc_cls": "PP-LCNet_x1_0_textline_ori-ONNX",
        },
    }
}

def get_model_path(model_type: str, component: str) -> Optional[str]:
    """
    获取模型路径，如果本地不存在则尝试下载

    Args:
        model_type: 模型类型，如 'pp_structure_v3'
        component: 组件名称，如 'layout_det', 'ocr_det'

    Returns:
        模型文件路径，如果失败返回None
    """
    if model_type not in PIPELINE_CONFIG or component not in PIPELINE_CONFIG[model_type]["models"]:
        return None

    model_name = PIPELINE_CONFIG[model_type]["models"][component]
    return get_model_path_from_registry(model_name)

def get_available_pipelines() -> list[str]:
    """
    获取所有可用的pipeline名称

    Returns:
        pipeline名称列表
    """
    return list(PIPELINE_CONFIG.keys())

def get_pipeline_models(pipeline_name: str) -> Dict[str, str]:
    """
    获取pipeline使用的模型路径映射

    Args:
        pipeline_name: pipeline名称，如 'pp_structure_v3'

    Returns:
        组件名称到模型文件路径的映射字典，只包含可用的模型
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

def get_pipeline_model_info(pipeline_name: str) -> Optional[Dict[str, Any]]:
    """
    获取pipeline的详细信息，包括所有模型信息

    Args:
        pipeline_name: pipeline名称

    Returns:
        包含模型信息和路径的字典，如果pipeline不存在返回None
    """
    if pipeline_name not in PIPELINE_CONFIG:
        return None

    pipeline_config = PIPELINE_CONFIG[pipeline_name]
    model_info = {
        "pipeline": pipeline_name,
        "models": {},
        "all_models_available": True
    }

    for component, model_name in pipeline_config["models"].items():
        model_path = get_model_path_from_registry(model_name)
        model_info["models"][component] = {
            "model_name": model_name,
            "path": model_path,
            "available": model_path is not None
        }
        if model_path is None:
            model_info["all_models_available"] = False

    return model_info

def validate_pipeline_config(pipeline_name: str) -> Dict[str, Any]:
    """
    验证pipeline配置是否正确，所有模型是否可用

    Args:
        pipeline_name: pipeline名称

    Returns:
        验证结果字典
    """
    result = {
        "pipeline": pipeline_name,
        "valid": False,
        "missing_models": [],
        "available_models": [],
        "errors": []
    }

    if pipeline_name not in PIPELINE_CONFIG:
        result["errors"].append(f"Pipeline '{pipeline_name}' not found in PIPELINE_CONFIG")
        return result

    pipeline_config = PIPELINE_CONFIG[pipeline_name]

    for component, model_name in pipeline_config["models"].items():
        if model_name not in MODEL_REGISTRY:
            result["errors"].append(f"Model '{model_name}' for component '{component}' not found in MODEL_REGISTRY")
            result["missing_models"].append(model_name)
        else:
            model_path = get_model_path_from_registry(model_name)
            if model_path:
                result["available_models"].append({
                    "component": component,
                    "model_name": model_name,
                    "path": model_path
                })
            else:
                result["missing_models"].append(model_name)

    result["valid"] = len(result["errors"]) == 0 and len(result["missing_models"]) == 0
    return result

def ensure_pipeline_models_available(pipeline_name: str, download_missing: bool = True) -> bool:
    """
    确保pipeline的所有模型都可用，如果需要则下载

    Args:
        pipeline_name: pipeline名称
        download_missing: 是否下载缺失的模型

    Returns:
        是否所有模型都可用
    """
    if pipeline_name not in PIPELINE_CONFIG:
        print(f"Pipeline '{pipeline_name}' not found")
        return False

    pipeline_config = PIPELINE_CONFIG[pipeline_name]
    all_available = True

    for component, model_name in pipeline_config["models"].items():
        model_path = get_model_path_from_registry(model_name)
        if model_path is None:
            if download_missing:
                print(f"Model '{model_name}' for component '{component}' is missing, attempting to download...")
                # download_model函数会自动处理下载
                model_path = get_model_path_from_registry(model_name)
                if model_path:
                    print(f"Successfully downloaded model '{model_name}'")
                else:
                    print(f"Failed to download model '{model_name}'")
                    all_available = False
            else:
                print(f"Model '{model_name}' for component '{component}' is not available")
                all_available = False

    return all_available

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

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """
    获取所有可用模型的信息

    Returns:
        模型名称到模型信息的映射字典
    """
    models_info = {}
    for model_name, config in MODEL_REGISTRY.items():
        model_path = get_model_path_from_registry(model_name)
        models_info[model_name] = {
            "config": config,
            "path": model_path,
            "available": model_path is not None
        }
    return models_info

def get_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """
    获取单个模型的详细信息

    Args:
        model_name: 模型名称

    Returns:
        模型信息字典，包含配置、路径和可用性
    """
    if model_name not in MODEL_REGISTRY:
        return None

    config = MODEL_REGISTRY[model_name]
    model_path = get_model_path_from_registry(model_name)

    return {
        "model_name": model_name,
        "config": config,
        "path": model_path,
        "available": model_path is not None,
        "local_path": config["local_path"]
    }

def list_pipeline_status() -> Dict[str, Dict[str, Any]]:
    """
    列出所有pipeline的状态

    Returns:
        pipeline名称到状态信息的映射字典
    """
    status = {}
    for pipeline_name in get_available_pipelines():
        status[pipeline_name] = validate_pipeline_config(pipeline_name)
    return status

def print_pipeline_info(pipeline_name: str) -> None:
    """
    打印pipeline的详细信息

    Args:
        pipeline_name: pipeline名称
    """
    info = get_pipeline_model_info(pipeline_name)
    if not info:
        print(f"Pipeline '{pipeline_name}' not found")
        return

    print(f"\n=== Pipeline: {pipeline_name} ===")
    print(f"All models available: {info['all_models_available']}")

    print("\nModels:")
    for component, model_info in info["models"].items():
        status = "✓" if model_info["available"] else "✗"
        path = model_info["path"] or "Not available"
        print(f"  {component}: {model_info['model_name']} {status}")
        print(f"    Path: {path}")

def print_all_models_status() -> None:
    """
    打印所有模型的状态
    """
    print("\n=== All Models Status ===")
    models_info = get_available_models()

    available_count = 0
    total_count = len(models_info)

    for model_name, info in models_info.items():
        if info["available"]:
            available_count += 1
            print(f"✓ {model_name}: {info['path']}")
        else:
            print(f"✗ {model_name}: Not available")

    print(f"\nTotal: {available_count}/{total_count} models available")