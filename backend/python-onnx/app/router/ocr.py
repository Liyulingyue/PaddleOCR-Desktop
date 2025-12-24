from fastapi import APIRouter, UploadFile, File, Form, Depends, Body
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
import json
import numpy as np
from ..deps import get_model
from ..core.utils import draw_ocr

try:
    import fitz  # pymupdf
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

router = APIRouter()


router = APIRouter()


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
    model=Depends(get_model),
    det_db_thresh: float = Form(0.3),
    cls_thresh: float = Form(0.9),
    use_cls: bool = Form(True)
):
    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""
    
    try:
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
                    # 临时更新模型配置
                    original_det_thresh = getattr(model.args, 'det_db_thresh', 0.3)
                    original_cls_thresh = getattr(model.args, 'cls_thresh', 0.9)
                    
                    # 更新阈值
                    model.args.det_db_thresh = det_db_thresh
                    model.args.cls_thresh = cls_thresh
                    
                    try:
                        result = model.ocr(img, cls=use_cls)
                        # 为每页的结果添加页面信息
                        page_result = {
                            "page": page_idx + 1,
                            "result": result
                        }
                        all_results.append(page_result)
                    finally:
                        # 恢复原始配置
                        model.args.det_db_thresh = original_det_thresh
                        model.args.cls_thresh = original_cls_thresh
                        
                except Exception as e:
                    return JSONResponse(status_code=500, content={"error": f"处理第{page_idx+1}页时出错: {str(e)}"})
            
            return {"result": all_results}
        else:
            # 处理图像文件
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img = np.array(img)
            
            # 临时更新模型配置
            original_det_thresh = getattr(model.args, 'det_db_thresh', 0.3)
            original_cls_thresh = getattr(model.args, 'cls_thresh', 0.9)
            
            # 更新阈值
            model.args.det_db_thresh = det_db_thresh
            model.args.cls_thresh = cls_thresh
            
            try:
                result = model.ocr(img, cls=use_cls)
            finally:
                # 恢复原始配置
                model.args.det_db_thresh = original_det_thresh
                model.args.cls_thresh = original_cls_thresh
                
            return {"result": result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.post("/draw")
async def draw_ocr_result(
    file: UploadFile = File(...), 
    ocr_result: str = Form(...),
    drop_score: float = Form(0.5)
):
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
            
            # 检查OCR结果格式 - 现在应该是多页格式
            if not ocr_data or "result" not in ocr_data:
                return JSONResponse(status_code=400, content={"error": "Invalid OCR result format"})
            
            drawn_pages = []
            for page_idx, img in enumerate(images):
                # 查找对应页面的OCR结果
                page_result = None
                if isinstance(ocr_data["result"], list) and len(ocr_data["result"]) > page_idx:
                    page_data = ocr_data["result"][page_idx]
                    if isinstance(page_data, dict) and "result" in page_data:
                        page_result = page_data["result"]
                
                if page_result and page_result and page_result[0]:
                    lines = page_result[0]
                    boxes = [line[0] for line in lines]
                    txts = [line[1][0] for line in lines]
                    scores = [line[1][1] for line in lines]
                    drawn_img = draw_ocr(img, boxes, txts, scores, drop_score=drop_score)
                    drawn_pages.append(drawn_img)
                else:
                    # 如果没有OCR结果，直接使用原图
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
                    "page": page_idx + 1,
                    "image": f"data:image/png;base64,{img_base64}"
                })
            
            return {"result": page_images}
        else:
            # 处理图像文件
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img_np = np.array(img)
            
            # 从ocr_result提取数据，格式: {"result": [[[box], [text, score]], ...]}
            if ocr_data and "result" in ocr_data and ocr_data["result"] and ocr_data["result"][0]:
                lines = ocr_data["result"][0]
                boxes = [line[0] for line in lines]
                txts = [line[1][0] for line in lines]
                scores = [line[1][1] for line in lines]
                drawn_img = draw_ocr(img_np, boxes, txts, scores, drop_score=drop_score)
                # Convert to PIL Image
                pil_img = Image.fromarray(drawn_img)
                # Save to BytesIO
                buf = io.BytesIO()
                pil_img.save(buf, format='PNG')
                buf.seek(0)
                return StreamingResponse(buf, media_type='image/png')
            else:
                return JSONResponse(status_code=400, content={"error": "Invalid OCR result format"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/ocr2text")
async def ocr_result_to_text(ocr_result: dict = Body(...)):
    """
    将OCR识别结果转换为纯文本格式
    
    参数:
    - ocr_result: OCR识别结果的JSON对象
    
    返回:
    - {"text": "提取的完整文本内容"}
    """
    try:
        if not ocr_result or "result" not in ocr_result:
            return JSONResponse(status_code=400, content={"error": "Invalid OCR result format"})
        
        result_data = ocr_result["result"]
        all_text_lines = []
        
        # 检查是否为多页PDF结果
        if isinstance(result_data, list) and len(result_data) > 0 and isinstance(result_data[0], dict) and "page" in result_data[0]:
            # 多页PDF结果 - 合并所有页面的文本
            for page_data in result_data:
                page_result = page_data.get("result", [])
                
                if page_result and isinstance(page_result, list) and len(page_result) > 0:
                    # 提取该页的所有文本行
                    for line in page_result[0] if page_result else []:
                        if isinstance(line, list) and len(line) >= 2:
                            text = line[1][0] if isinstance(line[1], list) and len(line[1]) >= 1 else ""
                            if text.strip():
                                all_text_lines.append(text)
        else:
            # 单页图像结果
            if result_data and isinstance(result_data, list) and len(result_data) > 0:
                for line in result_data[0] if result_data[0] else []:
                    if isinstance(line, list) and len(line) >= 2:
                        text = line[1][0] if isinstance(line[1], list) and len(line[1]) >= 1 else ""
                        if text.strip():
                            all_text_lines.append(text)
        
        # 合并所有文本行
        full_text = "\n".join(all_text_lines)
        return {"text": full_text}
                
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"文本提取失败: {str(e)}"})
