from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

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


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def metrics_prometheus() -> PlainTextResponse:
    return PlainTextResponse(
        content=metrics_store.prometheus_snapshot(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
