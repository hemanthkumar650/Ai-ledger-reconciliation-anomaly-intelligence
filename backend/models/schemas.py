from typing import Any

from pydantic import BaseModel, Field


class AnomalyResponse(BaseModel):
    transaction_id: str
    amount: float
    account: str
    anomaly_score: float = 0.0
    risk_level: str = "Unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnomalyListResponse(BaseModel):
    total: int
    offset: int = 0
    limit: int = 100
    items: list[AnomalyResponse]


class ExplainRequest(BaseModel):
    transaction_id: str | None = None
    transaction: AnomalyResponse | None = None


class ExplainResponse(BaseModel):
    transaction_id: str
    explanation: str
    risk_level: str
    possible_cause: str
    recommended_action: str


class AuditReportRequest(BaseModel):
    max_transactions: int = Field(default=50, ge=1, le=500)


class AuditReportResponse(BaseModel):
    summary: str
    total_flagged: int
    high_risk: int
    medium_risk: int
    low_risk: int


class AuditReportJobResponse(BaseModel):
    job_id: str
    status: str


class AuditReportJobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    result: AuditReportResponse | None = None
    error: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    max_transactions: int = Field(default=30, ge=1, le=200)


class ChatResponse(BaseModel):
    answer: str
