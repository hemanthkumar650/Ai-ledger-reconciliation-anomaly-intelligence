import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from backend.middleware.observability import ObservabilityMiddleware
from backend.routes import anomalies, audit_report, chat, explain, health
from backend.routes.dependencies import require_role
from backend.utils.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    app = FastAPI(
        title="AuditAI Backend",
        version="0.1.0",
        description="AI-Powered Ledger Reconciliation & Anomaly Intelligence API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ObservabilityMiddleware)

    @app.on_event("startup")
    async def validate_llm_config() -> None:
        if settings.llm_provider != "ollama":
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama startup check failed: {exc}") from exc

        models = payload.get("models", [])
        installed = {str(item.get("name", "")).strip() for item in models if isinstance(item, dict)}
        if settings.ollama_model not in installed:
            available = ", ".join(sorted(name for name in installed if name)) or "none"
            raise RuntimeError(
                f"Ollama model '{settings.ollama_model}' is not installed. Available models: {available}"
            )

    app.include_router(health.router, tags=["health"])
    app.include_router(
        anomalies.router,
        tags=["anomalies"],
        dependencies=[Depends(require_role("auditor", "admin"))],
    )
    app.include_router(
        explain.router,
        tags=["llm"],
        dependencies=[Depends(require_role("auditor", "admin"))],
    )
    app.include_router(
        audit_report.router,
        tags=["reports"],
        dependencies=[Depends(require_role("admin"))],
    )
    app.include_router(
        chat.router,
        tags=["chat"],
        dependencies=[Depends(require_role("auditor", "admin"))],
    )

    return app


app = create_app()
