from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import anomalies, audit_report, chat, explain, health
from backend.utils.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

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

    app.include_router(health.router, tags=["health"])
    app.include_router(anomalies.router, tags=["anomalies"])
    app.include_router(explain.router, tags=["llm"])
    app.include_router(audit_report.router, tags=["reports"])
    app.include_router(chat.router, tags=["chat"])

    return app


app = create_app()
