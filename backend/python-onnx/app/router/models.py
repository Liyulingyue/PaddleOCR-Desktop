from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Dict, Any
import os
from ..config import MODEL_REGISTRY, get_work_dir

def get_directory_size(path: Path) -> int:
    """
    计算目录的总大小（递归）
    """
    total_size = 0
    try:
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
            return total_size
    except (OSError, PermissionError):
        pass
    return 0

router = APIRouter()

@router.get("/list")
async def list_models() -> List[Dict[str, Any]]:
    """
    获取所有模型列表及其状态
    """
    work_dir = Path(get_work_dir())
    models = []

    for model_name, config in MODEL_REGISTRY.items():
        local_path = work_dir / config["local_path"]
        is_downloaded = local_path.exists()

        # 计算大小：文件直接获取，文件夹计算总大小
        size = 0
        if is_downloaded:
            size = get_directory_size(local_path)

        models.append({
            "name": model_name,
            "modelscope_id": config.get("modelscope_id", ""),
            "local_path": str(local_path),
            "is_downloaded": is_downloaded,
            "size": size
        })

    return models

@router.post("/download/{model_name}")
async def download_model(model_name: str):
    """
    下载指定模型
    """
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

    config = MODEL_REGISTRY[model_name]
    work_dir = Path(get_work_dir())
    local_path = work_dir / config["local_path"]

    try:
        # 确保父目录存在
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用ModelScope下载
        from modelscope import snapshot_download
        print(f"Downloading from ModelScope: {config['modelscope_id']}...")

        # 下载到临时目录（相对于work_dir）
        temp_cache_dir = work_dir / "temp"
        temp_dir = snapshot_download(
            config["modelscope_id"],
            cache_dir=str(temp_cache_dir)
        )

        temp_model_dir = Path(temp_dir)

        # 检查local_path是文件还是目录
        if local_path.suffix:  # 如果有扩展名，是文件路径
            # 查找inference.onnx文件
            inference_file = temp_model_dir / "inference.onnx"
            if inference_file.exists():
                # 复制文件到目标位置
                import shutil
                shutil.copy2(inference_file, local_path)
                print(f"Successfully downloaded {model_name} to {local_path}")
            else:
                # 如果没有inference.onnx，复制整个目录内容
                for item in temp_model_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, local_path.parent / item.name)
                print(f"Successfully downloaded {model_name} files to {local_path.parent}")
        else:  # 如果没有扩展名，是目录路径
            # 复制整个目录
            import shutil
            if local_path.exists():
                shutil.rmtree(local_path)
            shutil.copytree(temp_model_dir, local_path)
            print(f"Successfully downloaded {model_name} to {local_path}")

        # 清理整个临时缓存目录
        try:
            import shutil
            if temp_cache_dir.exists():
                shutil.rmtree(temp_cache_dir)
                print(f"Cleaned up temporary cache directory: {temp_cache_dir}")
        except Exception as cleanup_error:
            print(f"Warning: Failed to clean up temporary cache directory: {cleanup_error}")

        return {"message": f"Model {model_name} downloaded successfully"}

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ModelScope library not installed. Please install it with: pip install modelscope"
        )
    except Exception as e:
        print(f"Failed to download model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download model {model_name}: {str(e)}")

@router.delete("/delete/{model_name}")
async def delete_model(model_name: str):
    """
    删除指定模型文件
    """
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

    config = MODEL_REGISTRY[model_name]
    work_dir = Path(get_work_dir())
    local_path = work_dir / config["local_path"]

    try:
        if not local_path.exists():
            raise HTTPException(status_code=404, detail=f"Model {model_name} is not downloaded")

        import shutil
        if local_path.is_file():
            local_path.unlink()
            print(f"Deleted model file: {local_path}")
        else:
            shutil.rmtree(local_path)
            print(f"Deleted model directory: {local_path}")

        return {"message": f"Model {model_name} deleted successfully"}

    except Exception as e:
        print(f"Failed to delete model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete model {model_name}: {str(e)}")

@router.post("/batch-download")
async def batch_download_models(model_names: List[str]):
    """
    批量下载模型
    """
    if not model_names:
        raise HTTPException(status_code=400, detail="No models specified")

    results = []
    for model_name in model_names:
        try:
            # 复用单个下载的逻辑
            config = MODEL_REGISTRY.get(model_name)
            if not config:
                results.append({"model": model_name, "success": False, "error": "Model not found"})
                continue

            work_dir = Path(get_work_dir())
            local_path = work_dir / config["local_path"]

            # 确保父目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用ModelScope下载
            from modelscope import snapshot_download
            print(f"Downloading from ModelScope: {config['modelscope_id']}...")

            # 下载到临时目录（相对于work_dir）
            temp_cache_dir = work_dir / "temp"
            temp_dir = snapshot_download(
                config["modelscope_id"],
                cache_dir=str(temp_cache_dir)
            )

            temp_model_dir = Path(temp_dir)

            # 检查local_path是文件还是目录
            if local_path.suffix:  # 如果有扩展名，是文件路径
                # 查找inference.onnx文件
                inference_file = temp_model_dir / "inference.onnx"
                if inference_file.exists():
                    # 复制文件到目标位置
                    import shutil
                    shutil.copy2(inference_file, local_path)
                    print(f"Successfully downloaded {model_name} to {local_path}")
                    results.append({"model": model_name, "success": True})
                else:
                    # 如果没有inference.onnx，复制整个目录内容
                    for item in temp_model_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, local_path.parent / item.name)
                    print(f"Successfully downloaded {model_name} files to {local_path.parent}")
                    results.append({"model": model_name, "success": True})
            else:  # 如果没有扩展名，是目录路径
                # 复制整个目录
                import shutil
                if local_path.exists():
                    shutil.rmtree(local_path)
                shutil.copytree(temp_model_dir, local_path)
                print(f"Successfully downloaded {model_name} to {local_path}")
                results.append({"model": model_name, "success": True})

            # 清理临时目录
            try:
                import shutil
                if temp_cache_dir.exists():
                    shutil.rmtree(temp_cache_dir)
                    print(f"Cleaned up temporary cache directory: {temp_cache_dir}")
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temporary cache directory: {cleanup_error}")

        except Exception as e:
            print(f"Failed to download model {model_name}: {e}")
            results.append({"model": model_name, "success": False, "error": str(e)})

    return {"results": results}

@router.delete("/batch-delete")
async def batch_delete_models(model_names: List[str]):
    """
    批量删除模型
    """
    if not model_names:
        raise HTTPException(status_code=400, detail="No models specified")

    results = []
    for model_name in model_names:
        try:
            config = MODEL_REGISTRY.get(model_name)
            if not config:
                results.append({"model": model_name, "success": False, "error": "Model not found"})
                continue

            work_dir = Path(get_work_dir())
            local_path = work_dir / config["local_path"]

            if not local_path.exists():
                results.append({"model": model_name, "success": False, "error": "Model not downloaded"})
                continue

            import shutil
            if local_path.is_file():
                local_path.unlink()
                print(f"Deleted model file: {local_path}")
            else:
                shutil.rmtree(local_path)
                print(f"Deleted model directory: {local_path}")

            results.append({"model": model_name, "success": True})

        except Exception as e:
            print(f"Failed to delete model {model_name}: {e}")
            results.append({"model": model_name, "success": False, "error": str(e)})

    return {"results": results}