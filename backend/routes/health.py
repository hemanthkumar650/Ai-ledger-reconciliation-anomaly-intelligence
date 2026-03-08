from pathlib import Path

import httpx
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


async def _ollama_model_ready(base_url: str, model_name: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        return False, f"Ollama check failed: {exc}"

    models = payload.get("models", [])
    installed = {str(item.get("name", "")).strip() for item in models if isinstance(item, dict)}
    if model_name not in installed:
        available = ", ".join(sorted(name for name in installed if name)) or "none"
        return False, f"Model '{model_name}' not installed. Available: {available}"

    return True, "ok"


@router.get("/ready")
async def readiness_check() -> dict:
    settings = get_settings()
    dataset_ok = Path(settings.anomalies_csv_path).exists()

    provider = settings.llm_provider.strip().lower()
    llm_ok = False
    llm_detail = "Unsupported LLM provider"

    if provider == "azure":
        missing: list[str] = []
        if not settings.azure_openai_endpoint.strip():
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not settings.azure_openai_api_key.strip():
            missing.append("AZURE_OPENAI_API_KEY")
        if not settings.azure_openai_deployment.strip():
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        llm_ok = len(missing) == 0
        llm_detail = "ok" if llm_ok else f"Missing config: {', '.join(missing)}"
    elif provider == "ollama":
        base_url = settings.ollama_base_url.strip()
        model_name = settings.ollama_model.strip()
        if not base_url or not model_name:
            llm_ok = False
            llm_detail = "Missing OLLAMA_BASE_URL or OLLAMA_MODEL"
        else:
            llm_ok, llm_detail = await _ollama_model_ready(base_url, model_name)

    ready = dataset_ok and llm_ok
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "dataset": {
                "ok": dataset_ok,
                "path": settings.anomalies_csv_path,
            },
            "llm": {
                "ok": llm_ok,
                "provider": settings.llm_provider,
                "detail": llm_detail,
            },
        },
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
