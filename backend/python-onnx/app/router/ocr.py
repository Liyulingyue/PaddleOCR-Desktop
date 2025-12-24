from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
import json
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
async def draw_ocr_result(file: UploadFile = File(...), ocr_result: str = Form(...)):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img_np = np.array(img)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    try:
        # 解析ocr_result JSON字符串
        ocr_data = json.loads(ocr_result)
        # 从ocr_result提取数据，格式: {"result": [[[box], [text, score]], ...]}
        if ocr_data and "result" in ocr_data and ocr_data["result"] and ocr_data["result"][0]:
            lines = ocr_data["result"][0]
            boxes = [line[0] for line in lines]
            txts = [line[1][0] for line in lines]
            scores = [line[1][1] for line in lines]
            drawn_img = draw_ocr(img_np, boxes, txts, scores)
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
