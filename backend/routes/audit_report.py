from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import AuditReportRequest, AuditReportResponse
from backend.services.anomaly_service import AnomalyService, get_anomaly_service
from backend.services.llm_service import LLMService, get_llm_service

router = APIRouter()


@router.post("/audit-report", response_model=AuditReportResponse)
async def generate_audit_report(
    request: AuditReportRequest,
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> AuditReportResponse:
    anomalies = await anomaly_service.list_anomalies()
    subset = anomalies[: request.max_transactions]

    try:
        summary = await llm_service.generate_audit_report(subset)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc

    high = sum(1 for a in anomalies if a.risk_level.lower() == "high")
    medium = sum(1 for a in anomalies if a.risk_level.lower() == "medium")
    low = sum(1 for a in anomalies if a.risk_level.lower() == "low")

    return AuditReportResponse(
        summary=summary,
        total_flagged=len(anomalies),
        high_risk=high,
        medium_risk=medium,
        low_risk=low,
    )
