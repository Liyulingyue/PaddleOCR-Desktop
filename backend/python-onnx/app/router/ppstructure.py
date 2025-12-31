from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import numpy as np
from ..core.pp_doclayout_onnx import PPDocLayoutONNX

router = APIRouter()

# Global model instance
layout_model = None

def get_layout_model():
    global layout_model
    if layout_model is None:
        layout_model = PPDocLayoutONNX()
    return layout_model

@router.post("/")
async def detect_layout(
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.5)
):
    try:
        contents = await file.read()
        filename = file.filename.lower() if file.filename else ""

        # Only process image files
        if not filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            return JSONResponse(status_code=400, content={"error": "Only image files are supported"})

        # Load image
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = np.array(img)

        # Get model
        model = get_layout_model()

        # Run detection
        regions = model.detect(img, conf_threshold=conf_threshold)

        return {"result": regions}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/draw")
async def draw_layout_result(
    file: UploadFile = File(...),
    layout_result: str = Form(...)
):
    try:
        import json
        contents = await file.read()

        # Load image
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = np.array(img)

        # Parse layout result
        layout_data = json.loads(layout_result)
        regions = layout_data.get("result", [])

        # Get model for visualization
        model = get_layout_model()
        vis_image = model.visualize(img, regions)

        # Convert to bytes
        import cv2
        success, encoded_image = cv2.imencode('.png', cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
        if not success:
            return JSONResponse(status_code=500, content={"error": "Failed to encode image"})

        from fastapi.responses import StreamingResponse
        return StreamingResponse(io.BytesIO(encoded_image.tobytes()), media_type="image/png")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})