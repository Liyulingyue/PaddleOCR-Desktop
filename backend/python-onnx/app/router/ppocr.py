from fastapi import APIRouter, UploadFile, File, Form, Depends, Body
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
import json
import numpy as np
from ..core.utils import draw_ocr

# 导入新的pipeline
try:
    from ..core.pp_pileline.pp_ocrv5_pipeline import PPOCRv5Pipeline
    HAS_PIPELINE = True
except ImportError:
    HAS_PIPELINE = False

from ..config import get_work_dir

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

try:
    import fitz  # pymupdf
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

router = APIRouter()

def rotate_image(img, rotation_angle):
    """
    根据全局旋转角度旋转图像
    
    Args:
        img: numpy数组格式的图像
        rotation_angle: 旋转角度（度数）
    
    Returns:
        numpy数组: 旋转后的图像
    """
    if rotation_angle == 0:
        return img
    
    # 将numpy数组转换为PIL Image
    pil_img = Image.fromarray(img)
    
    # 旋转图像（逆时针旋转rotation_angle度）
    rotated_pil_img = pil_img.rotate(-rotation_angle, expand=True)
    
    # 转换回numpy数组
    rotated_img = np.array(rotated_pil_img)
    
    return rotated_img

def pdf_to_images_from_bytes(pdf_bytes, dpi=200):
    """将PDF字节数据转换为图像列表"""
    if not HAS_FITZ:
        raise RuntimeError("未安装pymupdf库，无法处理PDF文件。请先安装pymupdf。")
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            # 移除alpha通道
            img = img[:, :, :3]
        images.append(img)
    doc.close()
    return images


@router.post("/")
async def recognize(
    file: UploadFile = File(...),
    det_db_thresh: float = Form(0.3),
    cls_thresh: float = Form(0.9),
    use_cls: bool = Form(True),
    merge_overlaps: bool = Form(False),
    overlap_threshold: float = Form(0.9)
):
    """
    使用PP-OCRv5 Pipeline进行OCR识别（返回pipeline格式）

    Args:
        file: 上传的图像文件或PDF文件
        det_db_thresh: 检测阈值（保留参数以保持兼容性）
        cls_thresh: 分类阈值（保留参数以保持兼容性）
        use_cls: 是否使用分类（保留参数以保持兼容性）
        merge_overlaps: 是否合并重叠的文本框
        overlap_threshold: 合并重叠框的重叠度阈值（交集/最小面积）
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用，请检查依赖"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    try:
        # 获取或创建pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPOCRv5Pipeline(use_gpu=False)
            set_global_pipeline(pipeline)

        # 检查是否为PDF文件
        if filename.endswith('.pdf'):
            # 处理PDF文件
            if not HAS_FITZ:
                return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})

            images = pdf_to_images_from_bytes(contents, dpi=300)
            if not images:
                return JSONResponse(status_code=400, content={"error": "PDF文件没有有效页面"})

            # 对每一页进行OCR
            all_results = []
            for page_idx, img in enumerate(images):
                try:
                    # 使用pipeline进行OCR
                    page_results = pipeline.ocr(img, conf_threshold=det_db_thresh, cls_thresh=cls_thresh, use_cls=use_cls, merge_overlaps=merge_overlaps, overlap_threshold=overlap_threshold)

                    # 直接返回pipeline格式
                    formatted_results = []
                    for result in page_results:
                        if result['confidence'] >= 0.1:  # 过滤低置信度结果
                            formatted_result = {
                                "box": result["bbox"],
                                "text": result["text"],
                                "text_confidence": float(result["confidence"]),
                                "rotation": result["rotation"],
                                "rotation_confidence": float(result["rotation_confidence"]),
                                "text_direction": None  # 预留字段，用于将来添加文字方向信息
                            }
                            formatted_results.append(formatted_result)

                    # 为每页的结果添加页面信息
                    page_result = {
                        "page": page_idx + 1,
                        "results": formatted_results
                    }
                    all_results.append(page_result)

                except Exception as e:
                    return JSONResponse(status_code=500, content={"error": f"处理第{page_idx+1}页时出错: {str(e)}"})

            return {"results": all_results}
        else:
            # 处理图像文件
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img = np.array(img)

            # 使用pipeline进行OCR
            results = pipeline.ocr(img, conf_threshold=det_db_thresh, cls_thresh=cls_thresh, use_cls=use_cls, merge_overlaps=merge_overlaps, overlap_threshold=overlap_threshold)

            # 直接返回pipeline格式
            formatted_results = []
            for result in results:
                if result['confidence'] >= 0.1:  # 过滤低置信度结果
                    formatted_result = {
                        "box": result["bbox"],
                        "text": result["text"],
                        "text_confidence": float(result["confidence"]),
                        "rotation": result["rotation"],
                        "rotation_confidence": float(result["rotation_confidence"]),
                        "text_direction": None  # 预留字段，用于将来添加文字方向信息
                    }
                    formatted_results.append(formatted_result)

            return {"results": formatted_results}

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.post("/draw")
async def draw_ocr_result(
    file: UploadFile = File(...),
    ocr_result: str = Form(...),
    drop_score: float = Form(0.0),
    max_pages: int = Form(2)
):
    """
    绘制OCR结果（仅支持pipeline格式）

    Args:
        file: 上传的图像文件或PDF文件
        ocr_result: OCR结果的JSON字符串（pipeline格式）
        drop_score: 丢弃分数阈值（0.0表示不过滤，默认0.0）
        max_pages: 对于多页PDF，限制最多处理和返回的页面数（默认2页）
    """
    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    try:
        # 解析ocr_result JSON字符串
        ocr_data = json.loads(ocr_result)

        if filename.endswith('.pdf'):
            # 处理PDF文件
            if not HAS_FITZ:
                return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})

            images = pdf_to_images_from_bytes(contents, dpi=300)
            if not images:
                return JSONResponse(status_code=400, content={"error": "PDF文件没有有效页面"})

            # 限制处理的最大页面数
            total_pages = len(images)
            limited_images = images[:max_pages]

            print(f"PDF共有{total_pages}页，限制处理{max_pages}页，实际处理{len(limited_images)}页")

            drawn_pages = []
            for page_idx, img in enumerate(limited_images):
                # 仅支持pipeline格式
                if "results" in ocr_data and isinstance(ocr_data["results"], list):
                    results = ocr_data["results"]
                    
                    # 检查是否为多页PDF格式
                    if len(results) > 0 and isinstance(results[0], dict) and "page" in results[0]:
                        # 多页PDF格式，找到对应页面的结果
                        page_result = None
                        for page_data in results:
                            if page_data.get("page") == page_idx + 1:
                                page_result = page_data.get("results", [])
                                break
                        if page_result is None:
                            page_result = []
                    else:
                        # 单页格式（理论上PDF不应该有这个情况）
                        page_result = results

                    # 转换为draw_ocr期望的格式
                    boxes = []
                    txts = []
                    scores = []

                    # 提取该页的全局rotation角度
                    page_rotation = 0
                    if page_result and len(page_result) > 0 and isinstance(page_result[0], dict):
                        page_rotation = page_result[0].get("rotation", 0)

                    for result in page_result:
                        if isinstance(result, dict) and "box" in result and "text" in result:
                            if result.get("text_confidence", 0) >= drop_score:
                                boxes.append(result["box"])
                                txts.append(result["text"])
                                scores.append(result.get("text_confidence", 0))

                    if boxes:
                        # 根据页面的rotation角度旋转图像
                        rotated_img = rotate_image(img, page_rotation)
                        
                        # 在旋转后的图像上绘制OCR结果（只绘制边界框，不显示文字）
                        drawn_img = draw_ocr(rotated_img, boxes, txts=None, scores=None, drop_score=drop_score)
                        drawn_pages.append(drawn_img)
                    else:
                        drawn_pages.append(img)
                else:
                    # 如果没有有效的pipeline结果，直接使用原图
                    drawn_pages.append(img)

            # 为每一页生成单独的图片并返回
            page_images = []
            for page_idx, drawn_img in enumerate(drawn_pages):
                # Convert to PIL Image
                pil_img = Image.fromarray(drawn_img)
                # Save to BytesIO
                buf = io.BytesIO()
                pil_img.save(buf, format='PNG')
                buf.seek(0)
                # 将图片数据编码为base64
                import base64
                img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                page_images.append({
                    "page_number": page_idx + 1,
                    "data": img_base64
                })

            # 返回JSON格式的多页图片列表
            print(f"返回{len(page_images)}页的OCR绘制结果（总共{total_pages}页）")
            return {
                'file_type': 'pdf',
                'total_pages': total_pages,
                'processed_pages': len(page_images),
                'max_pages_limit': max_pages,
                'images': page_images
            }
        else:
            # 处理图像文件
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img_np = np.array(img)

            # 仅支持pipeline格式
            if "results" in ocr_data and isinstance(ocr_data["results"], list):
                results = ocr_data["results"]

                # 提取全局rotation角度
                global_rotation = 0
                if results and len(results) > 0 and isinstance(results[0], dict):
                    global_rotation = results[0].get("rotation", 0)

                # 转换为draw_ocr期望的格式
                boxes = []
                txts = []
                scores = []

                for result in results:
                    if isinstance(result, dict) and "box" in result and "text" in result:
                        if result.get("text_confidence", 0) >= drop_score:
                            boxes.append(result["box"])
                            txts.append(result["text"])
                            scores.append(result.get("text_confidence", 0))

                if boxes:
                    # 根据全局rotation角度旋转图像
                    rotated_img = rotate_image(img_np, global_rotation)
                    
                    # 在旋转后的图像上绘制OCR结果（只绘制边界框，不显示文字）
                    drawn_img = draw_ocr(rotated_img, boxes, txts=None, scores=None, drop_score=drop_score)
                    # Convert to PIL Image
                    pil_img = Image.fromarray(drawn_img)
                    # Save to BytesIO
                    buf = io.BytesIO()
                    pil_img.save(buf, format='PNG')
                    buf.seek(0)
                    return StreamingResponse(buf, media_type='image/png')
                else:
                    # 没有有效结果，返回原图
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    buf.seek(0)
                    return StreamingResponse(buf, media_type='image/png')
            else:
                return JSONResponse(status_code=400, content={"error": "Invalid OCR result format - expected pipeline format with 'results' field"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/ocr2text")
async def ocr_result_to_text(ocr_result: dict = Body(...)):
    """
    将OCR识别结果转换为纯文本格式（仅支持pipeline格式）

    参数:
    - ocr_result: OCR识别结果的JSON对象（pipeline格式）

    返回:
    - {"text": "提取的完整文本内容"}
    """
    try:
        if not ocr_result or "results" not in ocr_result:
            return JSONResponse(status_code=400, content={"error": "Invalid OCR result format - expected pipeline format with 'results' field"})

        all_text_lines = []

        # 仅支持pipeline格式
        results = ocr_result["results"]
        if not isinstance(results, list):
            return JSONResponse(status_code=400, content={"error": "Invalid OCR result format - 'results' should be a list"})

        for result in results:
            if isinstance(result, dict) and "text" in result:
                text = result["text"]
                confidence = result.get("text_confidence", 1.0)
                if text.strip() and confidence >= 0.1:  # 可以根据需要调整阈值
                    all_text_lines.append(text)

        # 合并所有文本行
        full_text = "\n".join(all_text_lines)
        return {"text": full_text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"文本提取失败: {str(e)}"})


@router.post("/load")
async def load_model():
    """加载OCR模型"""
    try:
        # 检查pipeline是否可用
        if not HAS_PIPELINE:
            return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

        # 检查模型文件是否存在
        from pathlib import Path
        models_dir = Path(get_work_dir())
        # 注意：模型路径应该是目录路径，模型类会自动在内部拼接 /inference.onnx
        det_model = models_dir / "models" / "PP-OCRv5_mobile_det-ONNX"
        rec_model = models_dir / "models" / "PP-OCRv5_mobile_rec-ONNX"
        cls_model = models_dir / "models" / "PP-LCNet_x1_0_doc_ori-ONNX"

        # 检查模型目录内是否存在 inference.onnx 文件
        missing_files = []
        if not (det_model / "inference.onnx").exists():
            missing_files.append("PP-OCRv5_mobile_det-ONNX/inference.onnx")
        if not (rec_model / "inference.onnx").exists():
            missing_files.append("PP-OCRv5_mobile_rec-ONNX/inference.onnx")
        if not (cls_model / "inference.onnx").exists():
            missing_files.append("PP-LCNet_x1_0_doc_ori-ONNX/inference.onnx")

        if missing_files:
            error_msg = f"模型文件不完整，缺少以下文件：\n" + "\n".join(f"  - {file}" for file in missing_files)
            return JSONResponse(status_code=500, content={"error": error_msg, "missing_files": missing_files})

        # 获取或创建全局pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPOCRv5Pipeline(
                det_model_path=str(det_model),
                rec_model_path=str(rec_model),
                cls_model_path=str(cls_model),
                use_gpu=False
            )
            set_global_pipeline(pipeline)

        # 加载模型
        if pipeline.load():
            return {"message": "OCR模型加载成功", "loaded": True}
        else:
            return JSONResponse(status_code=500, content={"error": "模型加载失败", "loaded": False})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load models: {str(e)}"})


@router.post("/download_missing")
async def download_missing_models():
    """下载缺失的OCR模型（仅下载，不加载到内存）"""
    try:
        from ..config import get_model_path_from_registry
        
        # 尝试获取所有模型路径，如果缺失会自动下载
        try:
            det_model = get_model_path_from_registry("PP-OCRv5_mobile_det-ONNX")
            rec_model = get_model_path_from_registry("PP-OCRv5_mobile_rec-ONNX")
            cls_model = get_model_path_from_registry("PP-LCNet_x1_0_doc_ori-ONNX")
            
            if not all([det_model, rec_model, cls_model]):
                missing = []
                if not det_model:
                    missing.append("PP-OCRv5_mobile_det-ONNX")
                if not rec_model:
                    missing.append("PP-OCRv5_mobile_rec-ONNX")
                if not cls_model:
                    missing.append("PP-LCNet_x1_0_doc_ori-ONNX")
                error_msg = f"模型下载失败，无法获取：{', '.join(missing)}"
                return JSONResponse(status_code=500, content={"error": error_msg})
            
            return {"message": "所有模型文件下载完成", "downloaded": True}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"模型下载过程中出错：{str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to download models: {str(e)}"})


@router.post("/unload")
async def unload_model_endpoint():
    """卸载OCR模型"""
    try:
        pipeline = get_global_pipeline()
        if pipeline is not None:
            if pipeline.unload():
                return {"message": "OCR模型卸载成功", "loaded": False}
            else:
                return JSONResponse(status_code=500, content={"error": "模型卸载失败"})
        else:
            return {"message": "没有已加载的模型", "loaded": False}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to unload model: {str(e)}"})


@router.get("/model_status")
async def model_status():
    """返回模型状态"""
    try:
        # 检查pipeline是否可用
        if not HAS_PIPELINE:
            return {"loaded": False, "message": "Pipeline功能不可用"}

        # 检查模型文件是否存在
        from pathlib import Path
        models_dir = Path(get_work_dir())
        # 注意：模型路径应该是目录路径，不需要加 /inference.onnx
        det_model = models_dir / "models" / "PP-OCRv5_mobile_det-ONNX"
        rec_model = models_dir / "models" / "PP-OCRv5_mobile_rec-ONNX"
        cls_model = models_dir / "models" / "PP-LCNet_x1_0_doc_ori-ONNX"

        # 检查模型目录内是否存在 inference.onnx 文件
        models_exist = all([(det_model / "inference.onnx").exists(), 
                           (rec_model / "inference.onnx").exists(), 
                           (cls_model / "inference.onnx").exists()])

        if not models_exist:
            return {
                "loaded": False,
                "message": "模型文件不完整",
                "mode": "pipeline"
            }

        # 检查模型是否已加载
        pipeline = get_global_pipeline()
        if pipeline is not None:
            try:
                is_loaded = pipeline.is_loaded()
                if is_loaded:
                    return {
                        "loaded": True,
                        "message": "Pipeline模式：模型已加载",
                        "mode": "pipeline"
                    }
                else:
                    return {
                        "loaded": False,
                        "message": "Pipeline模式：模型文件完整但未加载",
                        "mode": "pipeline"
                    }
            except Exception as e:
                return {
                    "loaded": False,
                    "message": f"Pipeline模式：检查模型状态时出错 - {str(e)}",
                    "mode": "pipeline"
                }
        else:
            return {
                "loaded": False,
                "message": "Pipeline模式：模型文件完整但未初始化",
                "mode": "pipeline"
            }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to get model status: {str(e)}"})
