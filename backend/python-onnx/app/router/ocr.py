from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
import numpy as np
from ..deps import get_model
from ..core.utils import draw_ocr

router = APIRouter()


@router.post("/")
async def recognize(file: UploadFile = File(...), model=Depends(get_model)):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = np.array(img)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        result = model.ocr(img)
        return {"result": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/draw")
async def recognize_and_draw(file: UploadFile = File(...), model=Depends(get_model)):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img_np = np.array(img)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        result = model.ocr(img_np)
        if result and result[0]:
            boxes = [line[0] for line in result[0]]
            txts = [line[1][0] for line in result[0]]
            scores = [line[1][1] for line in result[0]]
            drawn_img = draw_ocr(img_np, boxes, txts, scores)
            # Convert to PIL Image
            pil_img = Image.fromarray(drawn_img)
            # Save to BytesIO
            buf = io.BytesIO()
            pil_img.save(buf, format='PNG')
            buf.seek(0)
            return StreamingResponse(buf, media_type='image/png')
        else:
            return JSONResponse(status_code=400, content={"error": "No OCR results"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
