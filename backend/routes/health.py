from fastapi import APIRouter

from backend.utils.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "auditai-backend",
        "llm_provider": settings.llm_provider,
    }
