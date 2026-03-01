from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from backend.models.schemas import AuditReportResponse


@dataclass
class ReportJob:
    job_id: str
    status: str
    created_at: str
    updated_at: str
    result: AuditReportResponse | None = None
    error: str | None = None


class ReportJobService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, ReportJob] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(tz=UTC).isoformat()

    def create_job(self) -> ReportJob:
        with self._lock:
            now = self._now()
            job = ReportJob(
                job_id=str(uuid4()),
                status="pending",
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.job_id] = job
            return job

    def get_job(self, job_id: str) -> ReportJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.updated_at = self._now()

    def mark_completed(self, job_id: str, result: AuditReportResponse) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.result = result
            job.error = None
            job.updated_at = self._now()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.result = None
            job.error = error
            job.updated_at = self._now()


report_job_service = ReportJobService()
