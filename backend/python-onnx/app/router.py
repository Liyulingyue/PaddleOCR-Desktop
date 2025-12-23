from fastapi import APIRouter

from .api.health import router as health_router
from .api.ocr import router as ocr_router

router = APIRouter()
router.include_router(health_router, prefix="/health")
router.include_router(ocr_router, prefix="/ocr")
