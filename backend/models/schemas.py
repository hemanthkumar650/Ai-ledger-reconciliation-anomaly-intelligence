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
