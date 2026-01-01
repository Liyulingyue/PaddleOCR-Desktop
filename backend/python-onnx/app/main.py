from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .router.health import router as health_router
from .router.ppocr import router as ocr_router
from .router.ppstructure import router as ppstructure_router
from .router.models import router as models_router


app = FastAPI(title="PaddleOCR ONNX API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/health")
app.include_router(ocr_router, prefix="/api/ocr")
app.include_router(ppstructure_router, prefix="/api/ppstructure")
app.include_router(models_router, prefix="/api/models")
