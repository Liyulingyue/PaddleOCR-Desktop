from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
import io
import cv2
import numpy as np
from PIL import Image

from ..config import get_model_path_from_registry

try:
    from ..core.pp_onnx.pp_uvdoc_onnx import UVDocONNX
    HAS_UVDOC = True
except ImportError:
    HAS_UVDOC = False

_global_uvdoc = None

def get_global_uvdoc():
    global _global_uvdoc
    return _global_uvdoc

def set_global_uvdoc(model):
    global _global_uvdoc
    _global_uvdoc = model

router = APIRouter()


@router.post("/unwarp")
async def unwarp_document(
    file: UploadFile = File(...),
    use_gpu: bool = Form(False),
    gpu_id: int = Form(0),
):
    """文档图像纠偏 - 将弯曲/透视变形的文档图像纠正为正视图像"""
    if not HAS_UVDOC:
        return JSONResponse(
            status_code=500,
            content={"error": "UVDoc功能不可用，请检查依赖是否正确安装"}
        )

    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse(
                status_code=400,
                content={"error": "无法解析图片文件"}
            )

        uvdoc = get_global_uvdoc()
        if uvdoc is None:
            uvdoc_model_path = get_model_path_from_registry("UVDoc-ONNX")
            if uvdoc_model_path is None:
                return JSONResponse(
                    status_code=500,
                    content={"error": "UVDoc-ONNX 模型未找到，请前往模型管理页面下载"}
                )
            uvdoc = UVDocONNX(str(uvdoc_model_path), use_gpu=use_gpu, gpu_id=gpu_id)
            set_global_uvdoc(uvdoc)

        unwarped, elapsed = uvdoc.unwarp(img)

        result_img = cv2.imencode('.png', unwarped)[1]
        return StreamingResponse(
            io.BytesIO(result_img.tobytes()),
            media_type="image/png",
            headers={
                "X-Elapsed-Time": str(elapsed),
                "X-Original-Shape": f"{img.shape[0]},{img.shape[1]}",
                "X-Result-Shape": f"{unwarped.shape[0]},{unwarped.shape[1]}",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"文档纠偏失败：{str(e)}"}
        )


@router.post("/unwarp/load")
async def load_uvdoc_model(use_gpu: bool = Form(False), gpu_id: int = Form(0)):
    """预加载 UVDoc 模型到内存"""
    if not HAS_UVDOC:
        return JSONResponse(status_code=500, content={"error": "UVDoc功能不可用"})

    try:
        from pathlib import Path
        uvdoc_model = Path(get_model_path_from_registry("UVDoc-ONNX"))
        if not (uvdoc_model / "inference.onnx").exists():
            return JSONResponse(
                status_code=500,
                content={"error": "模型文件不完整，缺少 UVDoc-ONNX/inference.onnx", "missing_files": ["UVDoc-ONNX/inference.onnx"]}
            )

        uvdoc = get_global_uvdoc()
        if uvdoc is None:
            uvdoc = UVDocONNX(str(uvdoc_model), use_gpu=use_gpu, gpu_id=gpu_id)
            set_global_uvdoc(uvdoc)

        return {"message": "UVDoc 模型加载成功", "loaded": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"模型加载失败：{str(e)}"})


@router.post("/unwarp/download_missing")
async def download_missing_uvdoc():
    """下载缺失的 UVDoc 模型"""
    try:
        uvdoc_model = get_model_path_from_registry("UVDoc-ONNX")
        if uvdoc_model is None:
            return JSONResponse(
                status_code=500,
                content={"error": "模型下载失败，无法获取：UVDoc-ONNX"}
            )
        return {"message": "UVDoc 模型文件下载完成", "downloaded": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"模型下载过程中出错：{str(e)}"})


@router.post("/unwarp/unload")
async def unload_uvdoc_model():
    """卸载 UVDoc 模型"""
    global _global_uvdoc
    _global_uvdoc = None
    return {"message": "UVDoc 模型已卸载", "loaded": False}


@router.get("/unwarp/model_status")
async def get_uvdoc_model_status():
    """获取 UVDoc 模型状态"""
    global _global_uvdoc
    if _global_uvdoc is not None:
        return {"loaded": True}
    return {"loaded": False}
