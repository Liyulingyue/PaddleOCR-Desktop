from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import base64
import numpy as np
import cv2
import os
from typing import Optional

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from ..core.pp_vl import PaddleOCRVLPipeline, GenAIConfig
    HAS_PPVL = True
except ImportError as e:
    HAS_PPVL = False
    PPVL_IMPORT_ERROR = str(e)

try:
    from ..core.pp_vl.llama_manager_client import (
        LlamaManagerClient,
        get_default_models_dir,
        find_free_port,
    )
    HAS_LLAMA_MANAGER = True
except ImportError as e:
    HAS_LLAMA_MANAGER = False
    LLAMA_MANAGER_ERROR = str(e)

from ..config import get_work_dir, get_model_path_from_registry

_global_pipeline = None
_global_manager_client: Optional[LlamaManagerClient] = None


def get_global_pipeline():
    return _global_pipeline


def set_global_pipeline(pipeline):
    global _global_pipeline
    _global_pipeline = pipeline


def get_manager_client(
    manager_url: Optional[str] = None,
    manager_port: int = 8081,
) -> LlamaManagerClient:
    global _global_manager_client
    if _global_manager_client is None:
        _global_manager_client = LlamaManagerClient(
            manager_url=manager_url,
            manager_port=manager_port,
        )
    return _global_manager_client


def pdf_to_images(pdf_bytes, dpi=200):
    if not HAS_FITZ:
        raise RuntimeError("pymupdf not installed")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img = img[:, :, :3]
        images.append(img)
    doc.close()
    return images


router = APIRouter()


@router.post("/manager/start")
async def start_llama_server(
    model_path: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    mmproj_path: Optional[str] = Form(None),
    llama_manager_url: str = Form("http://127.0.0.1:8081"),
    host: str = Form("127.0.0.1"),
    port: Optional[int] = Form(None),
    ctx_size: int = Form(8192),
    n_gpu_layers: Optional[int] = Form(None),
    n_threads: Optional[int] = Form(None),
    batch_size: Optional[int] = Form(None),
    flash_attention: bool = Form(True),
    additional_args: Optional[str] = Form(None),
):
    if not HAS_LLAMA_MANAGER:
        raise HTTPException(
            status_code=500,
            detail=f"llama-manager client unavailable: {LLAMA_MANAGER_ERROR}",
        )

    client = LlamaManagerClient(manager_url=llama_manager_url)

    existing_url = client.get_server_url()
    if existing_url:
        return JSONResponse(content={
            "status": "already_running",
            "server_url": existing_url,
            "message": "llama-server is already running",
        })

    try:
        server_url = client.start_server(
            model_path=model_path,
            model_name=model_name,
            mmproj_path=mmproj_path,
            host=host,
            port=port,
            ctx_size=ctx_size,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            batch_size=batch_size,
            flash_attention=flash_attention,
            additional_args=additional_args,
            wait_ready=True,
            wait_timeout=120.0,
        )
        return JSONResponse(content={
            "status": "started",
            "server_url": server_url,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manager/stop")
async def stop_llama_server(
    llama_manager_url: str = Form("http://127.0.0.1:8081"),
):
    if not HAS_LLAMA_MANAGER:
        raise HTTPException(status_code=500, detail="llama-manager client unavailable")

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        client.stop_server()
        return JSONResponse(content={"status": "stopped"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manager/status")
async def get_manager_status(
    llama_manager_url: str = "http://127.0.0.1:8081",
):
    if not HAS_LLAMA_MANAGER:
        raise HTTPException(status_code=500, detail="llama-manager client unavailable")

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        status = client.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(content={"error": str(e), "running": False})


@router.get("/manager/models")
async def list_llama_models(
    llama_manager_url: str = "http://127.0.0.1:8081",
):
    if not HAS_LLAMA_MANAGER:
        raise HTTPException(status_code=500, detail="llama-manager client unavailable")

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        models = client.list_models()
        return JSONResponse(content={"models": models})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manager/health")
async def check_manager_health(
    llama_manager_url: str = "http://127.0.0.1:8081",
):
    if not HAS_LLAMA_MANAGER:
        return JSONResponse(content={"available": False})

    client = LlamaManagerClient(manager_url=llama_manager_url)
    return JSONResponse(content={"available": client.health()})


@router.post("/predict")
async def predict(
    file: UploadFile = File(...),
    layout_conf_threshold: float = Form(0.5),
    layout_model: Optional[str] = Form(None),
    use_layout_detection: bool = Form(True),
    merge_layout_blocks: bool = Form(True),
    max_new_tokens: int = Form(4096),
    temperature: float = Form(0.0),
    top_p: Optional[float] = Form(None),
    repetition_penalty: Optional[float] = Form(None),
    min_pixels: Optional[int] = Form(None),
    max_pixels: Optional[int] = Form(None),
    llama_manager_url: str = Form("http://127.0.0.1:8081"),
    model_path: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    layout_model_dir: Optional[str] = Form(None),
):
    if not HAS_PPVL:
        return JSONResponse(status_code=500, content={"error": f"PP-VL import error: {PPVL_IMPORT_ERROR}"})
    if not HAS_LLAMA_MANAGER:
        return JSONResponse(status_code=500, content={"error": f"llama-manager client error: {LLAMA_MANAGER_ERROR}"})

    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    if not (filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')) or filename.endswith('.pdf')):
        return JSONResponse(status_code=400, content={"error": "Unsupported file type"})

    try:
        if filename.endswith('.pdf'):
            images = pdf_to_images(contents)
        else:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            images = [np.array(img)]

        client = LlamaManagerClient(manager_url=llama_manager_url)
        server_url = client.get_server_url()

        if not server_url:
            if model_path or model_name:
                server_url = client.start_server(
                    model_path=model_path,
                    model_name=model_name,
                    wait_ready=True,
                    wait_timeout=120.0,
                )
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "llama-server is not running. Please start it first via /api/ppocr_vl/manager/start",
                        "hint": f"POST to {llama_manager_url}/start with model_path or model_name",
                    },
                )

        genai_config = GenAIConfig(
            backend="llama-cpp-server",
            server_url=server_url,
            max_concurrency=50,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            skip_special_tokens=True,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )

        layout_path = layout_model_dir
        if layout_path is None and use_layout_detection:
            layout_path = get_model_path_from_registry(layout_model) if layout_model else None

        pipeline = PaddleOCRVLPipeline(
            layout_model_path=layout_path,
            genai_config=genai_config,
            use_gpu=False,
            layout_threshold=layout_conf_threshold,
            merge_layout_blocks=merge_layout_blocks,
            use_doc_preprocessor=False,
        )

        if not pipeline.load():
            return JSONResponse(status_code=500, content={"error": "Failed to load pipeline models"})

        all_results = []
        for page_idx, img_array in enumerate(images):
            page_result = list(
                pipeline.predict(
                    img_array,
                    use_layout_detection=use_layout_detection,
                    layout_threshold=layout_conf_threshold,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                    min_pixels=min_pixels,
                    max_pixels=max_pixels,
                )
            )
            if page_result:
                page_result[0]["page_number"] = page_idx + 1
                page_result[0]["total_pages"] = len(images)
                all_results.append(page_result[0])

        pipeline.unload()

        if len(all_results) == 1:
            return all_results[0]
        else:
            return {
                "file_type": "pdf" if filename.endswith('.pdf') else "image",
                "total_pages": len(images),
                "pages": all_results,
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/markdown")
async def generate_markdown(
    file: UploadFile = File(...),
    analysis_result: str = Form(...),
):
    return JSONResponse(status_code=501, content={"error": "Not yet implemented"})


@router.post("/draw")
async def draw_result(
    file: UploadFile = File(...),
    analysis_result: str = Form(...),
):
    contents = await file.read()
    filename = file.filename.lower() if file.filename else ""

    try:
        analysis_data = json.loads(analysis_result)
        parsing_list = analysis_data.get("parsing_res_list", [])

        if filename.endswith('.pdf'):
            images = pdf_to_images(contents)
        else:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            images = [np.array(img)]

        if not images:
            return JSONResponse(status_code=400, content={"error": "No images found"})

        vis_image = images[0].copy()

        label_colors = {
            "text": (0, 255, 0),
            "table": (255, 0, 0),
            "image": (0, 0, 255),
            "formula": (255, 255, 0),
            "chart": (255, 0, 255),
            "paragraph": (0, 255, 128),
            "content": (128, 255, 0),
            "header_image": (186, 85, 211),
            "footer_image": (70, 130, 180),
        }

        for block in parsing_list:
            bbox = block.get("bbox", [])
            if len(bbox) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in bbox]
            label = block.get("label", "text")
            color = label_colors.get(label, (255, 255, 255))
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis_image, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        success, encoded = cv2.imencode('.png', cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
        if not success:
            return JSONResponse(status_code=500, content={"error": "Failed to encode image"})

        from fastapi.responses import StreamingResponse
        buf = io.BytesIO(encoded.tobytes())
        return StreamingResponse(buf, media_type='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/load")
async def load_model(
    llama_manager_url: str = Form("http://127.0.0.1:8081"),
    model_path: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    port: Optional[int] = Form(None),
):
    if not HAS_LLAMA_MANAGER:
        return JSONResponse(status_code=500, content={"error": "llama-manager client unavailable"})

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        if client.is_server_running():
            return JSONResponse(content={"message": "Already running", "loaded": True})

        server_url = client.start_server(
            model_path=model_path,
            model_name=model_name,
            port=port,
            wait_ready=True,
            wait_timeout=120.0,
        )
        return JSONResponse(content={"message": "Server started", "server_url": server_url, "loaded": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/unload")
async def unload_model(
    llama_manager_url: str = Form("http://127.0.0.1:8081"),
):
    if not HAS_LLAMA_MANAGER:
        return JSONResponse(status_code=500, content={"error": "llama-manager client unavailable"})

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        client.stop_server()
        return JSONResponse(content={"message": "Server stopped", "loaded": False})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/model_status")
async def model_status(
    llama_manager_url: str = "http://127.0.0.1:8081",
):
    if not HAS_LLAMA_MANAGER:
        return {"loaded": False, "message": "llama-manager client unavailable"}

    client = LlamaManagerClient(manager_url=llama_manager_url)
    try:
        status = client.get_status()
        return {
            "loaded": status.get("running", False),
            "server_url": status.get("server_url"),
            "model_name": status.get("model_name"),
            "pid": status.get("pid"),
        }
    except Exception:
        return {"loaded": False, "message": "Cannot connect to llama-manager"}


@router.get("/options")
async def get_options():
    return {
        "options": {
            "layout_model": [
                {"value": "PP-DocLayout-L-ONNX", "label": "PP-DocLayout-L-ONNX", "description": "Standard layout detection"},
                {"value": "PP-DocLayout-M-ONNX", "label": "PP-DocLayout-M-ONNX", "description": "Medium layout detection"},
                {"value": "PP-DocLayout-S-ONNX", "label": "PP-DocLayout-S-ONNX", "description": "Small layout detection"},
                {"value": "PP-DocLayout_plus-L-ONNX", "label": "PP-DocLayout_plus-L-ONNX", "description": "Plus layout detection"},
            ]
        },
        "defaults": {"layout_model": "PP-DocLayout-L-ONNX"},
    }
