from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.models.schemas import (
    AuditReportJobResponse,
    AuditReportJobStatusResponse,
    AuditReportRequest,
    AuditReportResponse,
)
from backend.services.anomaly_service import AnomalyService, get_anomaly_service
from backend.services.llm_service import LLMService, get_llm_service
from backend.services.report_job_service import report_job_service

router = APIRouter()


async def _build_report(
    request: AuditReportRequest,
    anomaly_service: AnomalyService,
    llm_service: LLMService,
) -> AuditReportResponse:
    anomalies = await anomaly_service.list_anomalies()
    subset = anomalies[: request.max_transactions]

    summary = await llm_service.generate_audit_report(subset)

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


@router.post("/audit-report", response_model=AuditReportResponse)
async def generate_audit_report(
    request: AuditReportRequest,
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> AuditReportResponse:
    try:
        return await _build_report(request, anomaly_service, llm_service)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc


@router.post("/audit-report/jobs", response_model=AuditReportJobResponse, status_code=202)
async def create_audit_report_job(
    request: AuditReportRequest,
    background_tasks: BackgroundTasks,
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> AuditReportJobResponse:
    job = report_job_service.create_job()

    async def _run_job() -> None:
        report_job_service.mark_running(job.job_id)
        try:
            result = await _build_report(request, anomaly_service, llm_service)
            report_job_service.mark_completed(job.job_id, result)
        except RuntimeError as exc:
            report_job_service.mark_failed(job.job_id, f"LLM service error: {exc}")
        except Exception as exc:  # pragma: no cover
            report_job_service.mark_failed(job.job_id, f"Unexpected error: {exc}")

    background_tasks.add_task(_run_job)
    return AuditReportJobResponse(job_id=job.job_id, status=job.status)


@router.get("/audit-report/jobs/{job_id}", response_model=AuditReportJobStatusResponse)
async def get_audit_report_job(job_id: str) -> AuditReportJobStatusResponse:
    job = report_job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return AuditReportJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
        error=job.error,
    )
