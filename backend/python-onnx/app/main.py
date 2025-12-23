from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .router.health import router as health_router
from .router.ocr import router as ocr_router


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
