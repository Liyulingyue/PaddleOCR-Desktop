from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import numpy as np

# 导入新的pipeline
try:
    from ..core.pp_pileline.pp_structurev3_pipeline import PPStructureV3Pipeline
    HAS_PIPELINE = True
except ImportError:
    HAS_PIPELINE = False

# 全局pipeline实例（用于保持加载状态）
_global_pipeline = None

def get_global_pipeline():
    """获取全局pipeline实例"""
    global _global_pipeline
    return _global_pipeline

def set_global_pipeline(pipeline):
    """设置全局pipeline实例"""
    global _global_pipeline
    _global_pipeline = pipeline

router = APIRouter()

@router.post("/")
async def analyze_structure(
    file: UploadFile = File(...),
    layout_conf_threshold: float = Form(0.5),
    ocr_det_db_thresh: float = Form(0.3),
    ocr_cls_thresh: float = Form(0.9),
    ocr_use_cls: bool = Form(True)
):
    """
    使用PP-StructureV3 Pipeline进行文档结构分析（返回layout格式）

    Args:
        file: 上传的图像文件
        layout_conf_threshold: 布局检测置信度阈值
        ocr_det_db_thresh: OCR检测阈值（保留参数以保持兼容性）
        ocr_cls_thresh: OCR分类阈值（保留参数以保持兼容性）
        ocr_use_cls: 是否使用OCR分类（保留参数以保持兼容性）
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用，请检查依赖"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    # Only process image files
    if not filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        return JSONResponse(status_code=400, content={"error": "Only image files are supported"})

    try:
        # 获取模型路径
        from pathlib import Path
        models_dir = Path(__file__).parent.parent.parent / "models" / "pp_structure_v3"
        layout_model_path = models_dir / "PP-DocLayout-L" / "inference.onnx"
        ocr_det_model = models_dir.parent / "ppocrv5" / "det" / "det.onnx"
        ocr_rec_model = models_dir.parent / "ppocrv5" / "rec" / "rec.onnx"
        ocr_cls_model = models_dir.parent / "ppocrv5" / "cls" / "cls.onnx"
        ocr_dict_path = models_dir.parent / "ppocrv5" / "ppocrv5_dict.txt"

        # 检查模型文件是否存在
        if not all([layout_model_path.exists(), ocr_det_model.exists(), ocr_rec_model.exists(), ocr_cls_model.exists(), ocr_dict_path.exists()]):
            return JSONResponse(status_code=500, content={"error": "模型文件不完整"})

        # 获取或创建pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPStructureV3Pipeline(
                layout_model_path=str(layout_model_path),
                ocr_det_model_path=str(ocr_det_model),
                ocr_rec_model_path=str(ocr_rec_model),
                ocr_cls_model_path=str(ocr_cls_model),
                ocr_rec_char_dict_path=str(ocr_dict_path),
                use_gpu=False,
                gpu_id=0
            )
            set_global_pipeline(pipeline)

        # 确保模型已加载
        if not pipeline.is_loaded():
            if not pipeline.load():
                return JSONResponse(status_code=500, content={"error": "模型加载失败"})

        # Load image
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = np.array(img)

        # Run structure analysis
        result = pipeline.analyze_structure(img, layout_conf_threshold=layout_conf_threshold)

        return {"results": result["layout_regions"]}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/draw")
async def draw_structure_result(
    file: UploadFile = File(...),
    layout_result: str = Form(...)
):
    """
    绘制PP-StructureV3结果（layout格式）

    Args:
        file: 上传的图像文件
        layout_result: 结构分析结果的JSON字符串（layout格式）
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

    contents = await file.read()

    try:
        # Load image
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = np.array(img)

        # Parse structure result
        structure_data = json.loads(layout_result)
        result = structure_data.get("results", [])

        # Get pipeline for visualization
        pipeline = get_global_pipeline()
        if pipeline is None:
            return JSONResponse(status_code=500, content={"error": "Pipeline未初始化"})

        # 确保模型已加载
        if not pipeline.is_loaded():
            if not pipeline.load():
                return JSONResponse(status_code=500, content={"error": "模型加载失败"})

        # Visualize result
        vis_image = pipeline.visualize(img, result)

        # Convert to bytes
        import cv2
        success, encoded_image = cv2.imencode('.png', cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
        if not success:
            return JSONResponse(status_code=500, content={"error": "Failed to encode image"})

        # Return as streaming response (same as OCR)
        from fastapi.responses import StreamingResponse
        buf = io.BytesIO(encoded_image.tobytes())
        return StreamingResponse(buf, media_type='image/png')

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/markdown")
async def generate_markdown(
    file: UploadFile = File(...),
    layout_result: str = Form(...)
):
    """
    根据PP-StructureV3结果生成Markdown文档

    Args:
        file: 上传的图像文件
        layout_result: 结构分析结果的JSON字符串（layout格式）
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

    contents = await file.read()

    try:
        # Load image
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(img)

        # Parse structure result
        structure_data = json.loads(layout_result)
        layout_regions = structure_data.get("results", [])

        # Get pipeline for markdown generation
        pipeline = get_global_pipeline()
        if pipeline is None:
            return JSONResponse(status_code=500, content={"error": "Pipeline未初始化"})

        # 确保模型已加载
        if not pipeline.is_loaded():
            if not pipeline.load():
                return JSONResponse(status_code=500, content={"error": "模型加载失败"})

        # Delegate to pipeline to create a source-like markdown
        try:
            # First run structure analysis to get complete results
            analysis_result = pipeline.analyze_structure(img_array, layout_conf_threshold=0.5)
            result_md = pipeline.result_to_markdown(img_array, analysis_result)
            return result_md
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Failed to generate markdown: {str(e)}"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/load")
async def load_model():
    """加载PP-StructureV3模型"""
    try:
        # 检查pipeline是否可用
        if not HAS_PIPELINE:
            return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

        # 检查模型文件是否存在
        from pathlib import Path
        models_dir = Path(__file__).parent.parent.parent / "models" / "pp_structure_v3"
        layout_model_path = models_dir / "PP-DocLayout-L" / "inference.onnx"
        ocr_det_model = models_dir.parent / "ppocrv5" / "det" / "det.onnx"
        ocr_rec_model = models_dir.parent / "ppocrv5" / "rec" / "rec.onnx"
        ocr_cls_model = models_dir.parent / "ppocrv5" / "cls" / "cls.onnx"
        ocr_dict_path = models_dir.parent / "ppocrv5" / "ppocrv5_dict.txt"

        if not all([layout_model_path.exists(), ocr_det_model.exists(), ocr_rec_model.exists(), ocr_cls_model.exists(), ocr_dict_path.exists()]):
            return JSONResponse(status_code=500, content={"error": "模型文件不完整"})

        # 获取或创建全局pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPStructureV3Pipeline(
                layout_model_path=str(layout_model_path),
                ocr_det_model_path=str(ocr_det_model),
                ocr_rec_model_path=str(ocr_rec_model),
                ocr_cls_model_path=str(ocr_cls_model),
                ocr_rec_char_dict_path=str(ocr_dict_path),
                use_gpu=False
            )
            set_global_pipeline(pipeline)

        # 加载模型
        if pipeline.load():
            return {"message": "PP-StructureV3模型加载成功", "loaded": True}
        else:
            return JSONResponse(status_code=500, content={"error": "模型加载失败", "loaded": False})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load models: {str(e)}"})


@router.post("/unload")
async def unload_model_endpoint():
    """卸载PP-StructureV3模型"""
    try:
        pipeline = get_global_pipeline()
        if pipeline is not None:
            if pipeline.unload():
                return {"message": "PP-StructureV3模型卸载成功", "loaded": False}
            else:
                return JSONResponse(status_code=500, content={"error": "模型卸载失败"})
        else:
            return {"message": "没有已加载的模型", "loaded": False}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to unload model: {str(e)}"})


@router.get("/model_status")
async def model_status():
    """返回PP-StructureV3模型状态"""
    try:
        # 检查pipeline是否可用
        if not HAS_PIPELINE:
            return {"loaded": False, "message": "Pipeline功能不可用"}

        # 检查模型文件是否存在
        from pathlib import Path
        models_dir = Path(__file__).parent.parent.parent / "models" / "pp_structure_v3"
        layout_model_path = models_dir / "PP-DocLayout-L" / "inference.onnx"
        ocr_det_model = models_dir.parent / "ppocrv5" / "det" / "det.onnx"
        ocr_rec_model = models_dir.parent / "ppocrv5" / "rec" / "rec.onnx"
        ocr_cls_model = models_dir.parent / "ppocrv5" / "cls" / "cls.onnx"
        ocr_dict_path = models_dir.parent / "ppocrv5" / "ppocrv5_dict.txt"

        models_exist = all([layout_model_path.exists(), ocr_det_model.exists(), ocr_rec_model.exists(), ocr_cls_model.exists(), ocr_dict_path.exists()])

        if not models_exist:
            return {
                "loaded": False,
                "message": "模型文件不完整",
                "mode": "pp-structure-v3"
            }

        # 检查模型是否已加载
        pipeline = get_global_pipeline()
        if pipeline is not None:
            try:
                is_loaded = pipeline.is_loaded()
                if is_loaded:
                    return {
                        "loaded": True,
                        "message": "PP-StructureV3模式：模型已加载",
                        "mode": "pp-structure-v3"
                    }
                else:
                    return {
                        "loaded": False,
                        "message": "PP-StructureV3模式：模型文件完整但未加载",
                        "mode": "pp-structure-v3"
                    }
            except Exception as e:
                return {
                    "loaded": False,
                    "message": f"PP-StructureV3模式：检查模型状态时出错 - {str(e)}",
                    "mode": "pp-structure-v3"
                }
        else:
            return {
                "loaded": False,
                "message": "PP-StructureV3模式：模型文件完整但未初始化",
                "mode": "pp-structure-v3"
            }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to get model status: {str(e)}"})