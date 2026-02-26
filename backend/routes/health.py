from fastapi import APIRouter

from backend.utils.config import get_settings
from backend.utils.metrics import metrics_store

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "auditai-backend",
        "llm_provider": settings.llm_provider,
    }


@router.get("/metrics")
async def metrics() -> dict:
    return metrics_store.snapshot()
