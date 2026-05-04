from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
import io
import cv2
import numpy as np
import base64

from ..config import get_model_path_from_registry

try:
    from ..core.pp_onnx.pp_formulanet_onnx import PPFormulaNetONNX
    HAS_FORMULA = True
except ImportError:
    HAS_FORMULA = False

_global_formula = None


def get_global_formula():
    global _global_formula
    return _global_formula


def set_global_formula(model):
    global _global_formula
    _global_formula = model


router = APIRouter()


@router.get("/recognize/model_options")
async def get_formula_model_options():
    """获取公式识别模型选项"""
    options = [
        {"value": "PP-FormulaNet_plus-M-ONNX", "label": "PP-FormulaNet plus-M (推荐)", "description": "平衡精度与速度，适合大多数场景"},
        {"value": "PP-FormulaNet_plus-S-ONNX", "label": "PP-FormulaNet plus-S (快速)", "description": "体积最小，速度最快，轻量优先"},
        {"value": "PP-FormulaNet_plus-L-ONNX", "label": "PP-FormulaNet plus-L (高精度)", "description": "最高精度，体积较大，适合复杂公式"},
        {"value": "PP-FormulaNet-L-ONNX", "label": "PP-FormulaNet L (高精度)", "description": "高精度非Plus版本，需768×768输入"},
    ]
    return {"options": options}


@router.post("/recognize")
async def recognize_formula(
    file: UploadFile = File(...),
    use_gpu: bool = Form(False),
    gpu_id: int = Form(0),
    model: str = Form("PP-FormulaNet_plus-M-ONNX"),
):
    """
    公式识别 - 将公式图像转换为 LaTeX 文本
    """
    if not HAS_FORMULA:
        return JSONResponse(
            status_code=500,
            content={"error": "公式识别功能不可用，请检查依赖是否正确安装"}
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

        formula_model_path = get_model_path_from_registry(model)
        if formula_model_path is None:
            return JSONResponse(
                status_code=500,
                content={"error": f"模型 {model} 未找到，请前往模型管理页面下载"}
            )

        formula = get_global_formula()
        if formula is None or formula._model_path != formula_model_path:
            formula = PPFormulaNetONNX(str(formula_model_path), use_gpu=use_gpu, gpu_id=gpu_id)
            set_global_formula(formula)

        latex, elapsed = formula.predict_latex(img)

        return JSONResponse(
            content={
                "latex": latex,
                "elapsed": elapsed,
                "input_size": formula.input_size,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"公式识别失败：{str(e)}"}
        )


@router.post("/recognize/load")
async def load_formula_model(use_gpu: bool = Form(False), gpu_id: int = Form(0), model: str = Form("PP-FormulaNet_plus-M-ONNX")):
    """预加载公式识别模型到内存"""
    if not HAS_FORMULA:
        return JSONResponse(status_code=500, content={"error": "公式识别功能不可用"})

    try:
        from pathlib import Path
        formula_model_path = get_model_path_from_registry(model)
        if formula_model_path is None:
            return JSONResponse(
                status_code=500,
                content={"error": f"模型 {model} 未找到"}
            )
        formula_model = Path(formula_model_path)
        if not (formula_model / "inference.onnx").exists():
            return JSONResponse(
                status_code=500,
                content={"error": f"模型文件不完整，缺少 {model}/inference.onnx", "missing_files": [f"{model}/inference.onnx"]}
            )

        formula = get_global_formula()
        if formula is None or formula._model_path != str(formula_model):
            formula = PPFormulaNetONNX(str(formula_model), use_gpu=use_gpu, gpu_id=gpu_id)
            set_global_formula(formula)

        return {"message": f"{model} 加载成功", "loaded": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"模型加载失败：{str(e)}"})


@router.post("/recognize/download_missing")
async def download_missing_formula():
    """下载缺失的公式识别模型"""
    try:
        formula_model = get_model_path_from_registry("PP-FormulaNet_plus-M-ONNX")
        if formula_model is None:
            return JSONResponse(
                status_code=500,
                content={"error": "模型下载失败，无法获取：PP-FormulaNet_plus-M-ONNX"}
            )
        return {"message": "公式识别模型文件下载完成", "downloaded": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"模型下载过程中出错：{str(e)}"})


@router.post("/recognize/unload")
async def unload_formula_model():
    """卸载公式识别模型"""
    global _global_formula
    _global_formula = None
    return {"message": "公式识别模型已卸载", "loaded": False}


@router.get("/recognize/model_status")
async def get_formula_model_status():
    """获取公式识别模型状态"""
    global _global_formula
    if _global_formula is not None:
        return {"loaded": True}
    return {"loaded": False}
