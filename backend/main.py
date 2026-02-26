import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.observability import ObservabilityMiddleware
from backend.routes import anomalies, audit_report, chat, explain, health
from backend.routes.dependencies import require_api_key
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

    app.include_router(health.router, tags=["health"])
    app.include_router(anomalies.router, tags=["anomalies"], dependencies=[Depends(require_api_key)])
    app.include_router(explain.router, tags=["llm"], dependencies=[Depends(require_api_key)])
    app.include_router(audit_report.router, tags=["reports"], dependencies=[Depends(require_api_key)])
    app.include_router(chat.router, tags=["chat"], dependencies=[Depends(require_api_key)])

    return app


app = create_app()
