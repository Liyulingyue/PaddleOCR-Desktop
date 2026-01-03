from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import numpy as np
import base64
import cv2

# 导入PDF处理库
try:
    import fitz  # pymupdf
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

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

router = APIRouter()

@router.post("/")
async def analyze_structure(
    file: UploadFile = File(...),
    layout_conf_threshold: float = Form(0.5),
    ocr_det_db_thresh: float = Form(0.3),
    unclip_ratio: float = Form(1.1),
    merge_overlaps: bool = Form(False),
    overlap_threshold: float = Form(0.9),
    merge_layout: bool = Form(False),
    layout_overlap_threshold: float = Form(0.9),
    use_cls: bool = Form(True),
    cls_thresh: float = Form(0.9)
):
    """
    使用PP-StructureV3 Pipeline进行文档结构分析（返回layout格式）

    Args:
        file: 上传的图像文件或PDF文件
        layout_conf_threshold: 布局检测置信度阈值
        ocr_det_db_thresh: OCR检测阈值（用于OCR文本识别）
        unclip_ratio: 裁剪区域扩大倍数，默认1.1倍，用于包含更多上下文
        merge_overlaps: 是否合并重叠的文本框
        overlap_threshold: 合并重叠框的重叠度阈值（交集/最小面积）        merge_layout: 是否合并重叠的布局检测框（仅同类型框会合并）
        layout_overlap_threshold: 合并布局框的重叠度阈值
        use_cls: 是否启用文档方向检测
        cls_thresh: 方向检测置信度阈值
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用，请检查依赖"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    # 检查是否为支持的文件类型
    if not (filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')) or filename.endswith('.pdf')):
        return JSONResponse(status_code=400, content={"error": "Only image files (PNG, JPG, JPEG, BMP, TIFF) and PDF files are supported"})

    try:
        # 获取或创建pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPStructureV3Pipeline(use_gpu=False, gpu_id=0)
            set_global_pipeline(pipeline)

        # 确保模型已加载
        if not pipeline.is_loaded():
            if not pipeline.load():
                return JSONResponse(status_code=500, content={"error": "模型加载失败"})

        # 处理文件输入
        if filename.endswith('.pdf'):
            # 处理PDF文件
            if not HAS_FITZ:
                return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})
            
            try:
                images = pdf_to_images_from_bytes(contents, dpi=300)
                if not images:
                    return JSONResponse(status_code=400, content={"error": "PDF文件没有有效页面"})
                
                # 处理多页PDF，对每一页分别进行分析
                all_results = []
                for page_idx, img in enumerate(images):
                    print(f"处理PDF文件：{filename}，第{page_idx + 1}/{len(images)}页")
                    
                    # 对每一页进行结构分析
                    page_result = pipeline.analyze_structure(
                        img,
                        layout_conf_threshold=layout_conf_threshold,
                        ocr_conf_threshold=ocr_det_db_thresh,
                        unclip_ratio=unclip_ratio,
                        merge_overlaps=merge_overlaps,
                        overlap_threshold=overlap_threshold,
                        merge_layout=merge_layout,
                        layout_overlap_threshold=layout_overlap_threshold,
                        use_cls=use_cls,
                        cls_thresh=cls_thresh
                    )
                    
                    # 添加页面信息
                    page_result['page_number'] = page_idx + 1
                    page_result['total_pages'] = len(images)
                    page_result['is_from_pdf'] = True
                    
                    all_results.append(page_result)
                
                # 如果只有一页，直接返回该页结果；多页则返回包含所有页面的结果
                if len(all_results) == 1:
                    result = all_results[0]
                else:
                    result = {
                        'file_type': 'pdf',
                        'total_pages': len(images),
                        'pages': all_results
                    }
                
                print("Structure Analysis Result:", result)
                return result
                
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": f"PDF处理失败: {str(e)}"})
        else:
            # 处理图像文件
            try:
                img = Image.open(io.BytesIO(contents)).convert("RGB")
                img = np.array(img)
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": f"图像处理失败: {str(e)}"})

            # Run structure analysis on image
            result = pipeline.analyze_structure(
                img,
                layout_conf_threshold=layout_conf_threshold,
                ocr_conf_threshold=ocr_det_db_thresh,  # 使用检测阈值作为OCR阈值
                unclip_ratio=unclip_ratio,
                merge_overlaps=merge_overlaps,
                overlap_threshold=overlap_threshold,
                merge_layout=merge_layout,
                layout_overlap_threshold=layout_overlap_threshold,
                use_cls=use_cls,
                cls_thresh=cls_thresh
            )

            print("Structure Analysis Result:", result)

            return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/draw")
async def draw_structure_result(
    file: UploadFile = File(...),
    analysis_result: str = Form(...),
    page_number: int = Form(1),
    max_pages: int = Form(2)
):
    """
    绘制PP-StructureV3结果，对于多页PDF返回所有页面的图片列表

    Args:
        file: 上传的图像文件或PDF文件
        analysis_result: 完整结构分析结果的JSON字符串
        page_number: 对于单页PDF的可视化指定页码（仅在手动选择时使用）
        max_pages: 对于多页PDF，限制最多处理和返回的页面数（默认2页）
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    try:
        # Parse analysis result
        analysis_data = json.loads(analysis_result)

        # Get pipeline for visualization
        pipeline = get_global_pipeline()
        if pipeline is None:
            return JSONResponse(status_code=500, content={"error": "Pipeline未初始化"})

        # 确保模型已加载
        if not pipeline.is_loaded():
            if not pipeline.load():
                return JSONResponse(status_code=500, content={"error": "模型加载失败"})

        # 处理多页PDF的情况
        if analysis_data.get('file_type') == 'pdf':
            # 多页PDF结果 - 绘制所有页面（受max_pages限制）
            pages = analysis_data.get('pages', [])
            if not pages:
                return JSONResponse(status_code=400, content={"error": "PDF分析结果中没有页面数据"})
            
            # 获取PDF的所有页面图像
            if not HAS_FITZ:
                return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})
            
            try:
                images = pdf_to_images_from_bytes(contents, dpi=300)
                if len(images) != len(pages):
                    return JSONResponse(status_code=400, content={"error": f"PDF页面数({len(images)})与分析结果页面数({len(pages)})不匹配"})
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": f"PDF重新处理失败: {str(e)}"})
            
            # 限制处理的最大页面数
            total_pages = len(images)
            limited_pages = pages[:max_pages]
            limited_images = images[:max_pages]
            
            print(f"PDF共有{total_pages}页，限制处理{max_pages}页，实际处理{len(limited_pages)}页")
            
            # 为每一页绘制可视化结果
            all_drawn_images = []
            
            for page_idx, (img, page_data) in enumerate(zip(limited_images, limited_pages)):
                print(f"绘制PDF第{page_idx + 1}页的可视化结果")
                
                # 获取该页的区域和旋转信息
                layout_regions = page_data.get("layout_regions", [])
                rotation = page_data.get('rotation', 0)
                
                print(f"  页面{page_idx + 1}：有{len(layout_regions)}个区域，旋转度数{rotation}°")
                
                # 根据旋转信息处理图像
                if rotation == 90:
                    vis_image = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif rotation == 180:
                    vis_image = cv2.rotate(img, cv2.ROTATE_180)
                elif rotation == 270:
                    vis_image = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                else:
                    vis_image = img.copy()
                
                # 可视化结果
                visualized_image = pipeline.visualize(vis_image, layout_regions)
                
                # 转换为PNG字节
                success, encoded_image = cv2.imencode('.png', cv2.cvtColor(visualized_image, cv2.COLOR_RGB2BGR))
                if not success:
                    print(f"  错误：第{page_idx + 1}页图像编码失败")
                    return JSONResponse(status_code=500, content={"error": f"第{page_idx + 1}页图像编码失败"})
                
                # 转换为base64（encoded_image已经是numpy数组，直接转换）
                image_base64 = base64.b64encode(encoded_image).decode('utf-8')
                
                print(f"  页面{page_idx + 1}编码完成，base64长度: {len(image_base64)}")
                
                all_drawn_images.append({
                    'page_number': page_idx + 1,
                    'total_pages': total_pages,  # 返回实际总页数
                    'data': image_base64
                })
            
            # 返回JSON格式的多页图片列表
            print(f"返回{len(all_drawn_images)}页的绘制结果（总共{total_pages}页）")
            return {
                'file_type': 'pdf',
                'total_pages': total_pages,
                'processed_pages': len(all_drawn_images),
                'max_pages_limit': max_pages,
                'images': all_drawn_images
            }
        
        else:
            # 处理单个图像或单页PDF
            if filename.endswith('.pdf'):
                # 处理PDF文件
                if not HAS_FITZ:
                    return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})
                
                try:
                    images = pdf_to_images_from_bytes(contents, dpi=300)
                    if not images:
                        return JSONResponse(status_code=400, content={"error": "PDF文件没有有效页面"})
                    
                    # 选择指定的页面（从1开始计数）
                    if page_number < 1 or page_number > len(images):
                        return JSONResponse(status_code=400, content={"error": f"页面编号无效。PDF共有{len(images)}页，请求的是第{page_number}页"})
                    
                    img = images[page_number - 1]  # 转换为0-based索引
                    print(f"处理PDF文件：{filename}，可视化第{page_number}/{len(images)}页")
                except Exception as e:
                    return JSONResponse(status_code=400, content={"error": f"PDF处理失败: {str(e)}"})
            else:
                # 处理图像文件
                try:
                    img = Image.open(io.BytesIO(contents)).convert("RGB")
                    img = np.array(img)
                except Exception as e:
                    return JSONResponse(status_code=400, content={"error": f"图像处理失败: {str(e)}"})

            # 获取布局区域和旋转信息
            layout_regions = analysis_data.get("layout_regions", [])
            rotation = analysis_data.get('rotation', 0)
            
            # 根据旋转信息处理图像
            if rotation == 90:
                vis_image = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif rotation == 180:
                vis_image = cv2.rotate(img, cv2.ROTATE_180)
            elif rotation == 270:
                vis_image = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            else:
                vis_image = img.copy()

            # Visualize result
            visualized_image = pipeline.visualize(vis_image, layout_regions)

            # Convert to bytes
            success, encoded_image = cv2.imencode('.png', cv2.cvtColor(visualized_image, cv2.COLOR_RGB2BGR))
            if not success:
                return JSONResponse(status_code=500, content={"error": "Failed to encode image"})

            # Return as streaming response for single image
            from fastapi.responses import StreamingResponse
            buf = io.BytesIO(encoded_image.tobytes())
            return StreamingResponse(buf, media_type='image/png')

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/markdown")
async def generate_markdown(
    file: UploadFile = File(...),
    analysis_result: str = Form(...)
):
    """
    根据PP-StructureV3完整分析结果生成Markdown文档

    Args:
        file: 上传的图像文件或PDF文件
        analysis_result: 完整结构分析结果的JSON字符串
    """
    if not HAS_PIPELINE:
        return JSONResponse(status_code=500, content={"error": "Pipeline功能不可用"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    try:
        # Parse analysis result
        analysis_data = json.loads(analysis_result)

        # 处理多页PDF的情况
        if analysis_data.get('file_type') == 'pdf':
            # 多页PDF结果
            pages = analysis_data.get('pages', [])
            if not pages:
                return JSONResponse(status_code=400, content={"error": "PDF分析结果中没有页面数据"})
            
            # 获取PDF的所有页面图像
            if not HAS_FITZ:
                return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})
            
            try:
                images = pdf_to_images_from_bytes(contents, dpi=300)
                if len(images) != len(pages):
                    return JSONResponse(status_code=400, content={"error": f"PDF页面数({len(images)})与分析结果页面数({len(pages)})不匹配"})
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": f"PDF重新处理失败: {str(e)}"})
            
            # Get pipeline for markdown generation
            pipeline = get_global_pipeline()
            if pipeline is None:
                return JSONResponse(status_code=500, content={"error": "Pipeline未初始化"})
            
            # 确保模型已加载
            if not pipeline.is_loaded():
                if not pipeline.load():
                    return JSONResponse(status_code=500, content={"error": "模型加载失败"})
            
            # 为每一页生成markdown内容
            all_markdown_parts = []
            all_images = []
            image_counter = 0
            
            for page_idx, (img, page_data) in enumerate(zip(images, pages)):
                print(f"生成PDF第{page_idx + 1}页的markdown内容")
                
                # 为每一页生成markdown
                page_result = pipeline.result_to_markdown(img, page_data)
                page_markdown = page_result.get('markdown', '')
                page_images = page_result.get('images', [])
                
                # 重新编号图片文件名以避免冲突，并更新markdown中的引用
                for img_data in page_images:
                    old_filename = img_data['filename']
                    new_filename = f"page_{page_idx + 1}_{old_filename}"
                    img_data['filename'] = new_filename
                    
                    # 更新markdown中的图片引用
                    page_markdown = page_markdown.replace(f"images/{old_filename}", f"images/{new_filename}")
                
                # 顺次添加markdown内容（不添加页面分隔符和页码标题）
                if page_idx > 0:
                    # 不同页面之间添加换行，但不显示页码
                    all_markdown_parts.append("\n\n")
                
                all_markdown_parts.append(page_markdown)
                all_images.extend(page_images)
            
            # 合并所有markdown内容
            final_markdown = ''.join(all_markdown_parts)
            
            return {
                'markdown': final_markdown,
                'images': all_images
            }
        
        else:
            # 单页处理（图像文件或单页PDF）
            # 处理文件输入
            if filename.endswith('.pdf'):
                # 处理PDF文件
                if not HAS_FITZ:
                    return JSONResponse(status_code=400, content={"error": "未安装pymupdf库，无法处理PDF文件"})
                
                try:
                    images = pdf_to_images_from_bytes(contents, dpi=300)
                    if not images:
                        return JSONResponse(status_code=400, content={"error": "PDF文件没有有效页面"})
                    
                    img_array = images[0]
                    print(f"处理PDF文件：{filename}，共{len(images)}页，使用第1页")
                except Exception as e:
                    return JSONResponse(status_code=400, content={"error": f"PDF处理失败: {str(e)}"})
            else:
                # 处理图像文件
                try:
                    img = Image.open(io.BytesIO(contents)).convert("RGB")
                    img_array = np.array(img)
                except Exception as e:
                    return JSONResponse(status_code=400, content={"error": f"图像处理失败: {str(e)}"})

            # Get pipeline for markdown generation
            pipeline = get_global_pipeline()
            if pipeline is None:
                return JSONResponse(status_code=500, content={"error": "Pipeline未初始化"})

            # 确保模型已加载
            if not pipeline.is_loaded():
                if not pipeline.load():
                    return JSONResponse(status_code=500, content={"error": "模型加载失败"})

            # Delegate to pipeline to create markdown directly from analysis result
            try:
                print(f"Calling result_to_markdown with image shape: {img_array.shape}")
                print(f"Analysis data keys: {list(analysis_data.keys())}")
                result_md = pipeline.result_to_markdown(img_array, analysis_data)
                print(f"Generated markdown length: {len(result_md.get('markdown', ''))}")
                print(f"Markdown preview: {result_md.get('markdown', '')[:200]}")
                return result_md
            except Exception as e:
                print(f"Error in result_to_markdown: {str(e)}")
                import traceback
                traceback.print_exc()
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
        models_dir = Path(__file__).parent.parent.parent / "models"
        layout_model_path = models_dir / "PP-DocLayout-L-ONNX" / "inference.onnx"
        ocr_det_model = models_dir / "PP-OCRv5_mobile_det-ONNX" / "inference.onnx"
        ocr_rec_model = models_dir / "PP-OCRv5_mobile_rec-ONNX" / "inference.onnx"
        ocr_cls_model = models_dir / "PP-LCNet_x1_0_doc_ori-ONNX" / "inference.onnx"

        missing_files = []
        if not layout_model_path.exists():
            missing_files.append("PP-DocLayout-L-ONNX/inference.onnx")
        if not ocr_det_model.exists():
            missing_files.append("PP-OCRv5_mobile_det-ONNX/inference.onnx")
        if not ocr_rec_model.exists():
            missing_files.append("PP-OCRv5_mobile_rec-ONNX/inference.onnx")
        if not ocr_cls_model.exists():
            missing_files.append("PP-LCNet_x1_0_doc_ori-ONNX/inference.onnx")

        if missing_files:
            error_msg = f"模型文件不完整，缺少以下文件：\n" + "\n".join(f"  - {file}" for file in missing_files)
            return JSONResponse(status_code=500, content={"error": error_msg, "missing_files": missing_files})

        # 获取或创建全局pipeline实例
        pipeline = get_global_pipeline()
        if pipeline is None:
            pipeline = PPStructureV3Pipeline(
                layout_model_path=str(layout_model_path),
                ocr_det_model_path=str(ocr_det_model),
                ocr_rec_model_path=str(ocr_rec_model),
                ocr_cls_model_path=str(ocr_cls_model),
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
        models_dir = Path(__file__).parent.parent.parent / "models"
        layout_model_path = models_dir / "PP-DocLayout-L-ONNX" / "inference.onnx"
        ocr_det_model = models_dir / "PP-OCRv5_mobile_det-ONNX" / "inference.onnx"
        ocr_rec_model = models_dir / "PP-OCRv5_mobile_rec-ONNX" / "inference.onnx"
        ocr_cls_model = models_dir / "PP-LCNet_x1_0_doc_ori-ONNX" / "inference.onnx"

        models_exist = all([layout_model_path.exists(), ocr_det_model.exists(), ocr_rec_model.exists(), ocr_cls_model.exists()])

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