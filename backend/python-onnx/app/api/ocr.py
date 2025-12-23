from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import io

from ..deps import get_model

router = APIRouter()


@router.post("/")
async def recognize(file: UploadFile = File(...), model=Depends(get_model)):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    result = model.ocr(img)
    return {"result": result}
