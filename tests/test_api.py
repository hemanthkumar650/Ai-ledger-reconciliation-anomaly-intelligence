from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.schemas import AnomalyResponse
from backend.services.anomaly_service import get_anomaly_service
from backend.services.llm_service import get_llm_service
from backend.utils.config import get_settings
from backend.utils.metrics import metrics_store


class StubAnomalyService:
    async def get_by_transaction_id(self, transaction_id: str):
        if transaction_id == "T100":
            return AnomalyResponse(
                transaction_id="T100",
                amount=1000.0,
                account="4000",
                anomaly_score=0.9,
                risk_level="High",
                metadata={},
            )
        return None

    async def list_anomalies(self):
        return [
            AnomalyResponse(
                transaction_id="T100",
                amount=1000.0,
                account="4000",
                anomaly_score=0.9,
                risk_level="High",
                metadata={},
            )
        ]


class StubLLMService:
    async def explain_anomaly(self, anomaly: AnomalyResponse):
        return {
            "explanation": "Potential outlier",
            "risk_level": "High",
            "possible_cause": "Unexpected posting",
            "recommended_action": "Review source document",
        }

    async def generate_audit_report(self, anomalies):
        return "Summary"

    async def chat_with_ledger(self, question: str, anomalies, max_rows: int = 30):
        return "Answer"


def _build_client():
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_anomaly_service] = lambda: StubAnomalyService()
    app.dependency_overrides[get_llm_service] = lambda: StubLLMService()
    return TestClient(app)


def test_explain_rejects_mismatch_payload():
    client = _build_client()
    response = client.post(
        "/explain",
        json={
            "transaction_id": "T999",
            "transaction": {
                "transaction_id": "T100",
                "amount": 1000.0,
                "account": "4000",
                "anomaly_score": 0.9,
                "risk_level": "High",
                "metadata": {},
            },
        },
    )
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_explain_requires_transaction_input():
    client = _build_client()
    response = client.post("/explain", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Provide transaction_id or transaction payload"


def test_api_key_enforced_when_configured(monkeypatch):
    metrics_store.reset()
    monkeypatch.setenv("API_KEY", "secret-key")
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    unauthorized = client.get("/anomalies")
    authorized = client.get("/anomalies", headers={"x-api-key": "secret-key"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_metrics_endpoint_returns_request_counters(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    client.get("/health")
    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    body = metrics.json()
    assert "requests" in body
    assert body["requests"]["GET /health"]["count"] >= 1


def test_prometheus_metrics_endpoint_returns_exposition(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    client.get("/health")
    response = client.get("/metrics/prometheus")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "auditai_http_requests_total" in response.text
    assert "method=\"GET\",path=\"/health\"" in response.text
