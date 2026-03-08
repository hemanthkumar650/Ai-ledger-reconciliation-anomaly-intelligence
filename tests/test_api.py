import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
import backend.routes.health as health_module
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


class StubLLMErrorService(StubLLMService):
    async def explain_anomaly(self, anomaly: AnomalyResponse):
        raise RuntimeError("provider unavailable")

    async def chat_with_ledger(self, question: str, anomalies, max_rows: int = 30):
        raise RuntimeError("provider unavailable")


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
    monkeypatch.delenv("API_KEYS", raising=False)
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    unauthorized = client.get("/anomalies")
    authorized = client.get("/anomalies", headers={"x-api-key": "secret-key"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_role_based_access_enforced_with_api_keys(monkeypatch):
    metrics_store.reset()
    monkeypatch.setenv("API_KEYS", '{"auditor-key":"auditor","admin-key":"admin"}')
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    auditor_report = client.post("/audit-report", headers={"x-api-key": "auditor-key"}, json={"max_transactions": 5})
    admin_report = client.post("/audit-report", headers={"x-api-key": "admin-key"}, json={"max_transactions": 5})

    assert auditor_report.status_code == 403
    assert admin_report.status_code in (200, 502)


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


def test_ready_endpoint_reports_not_ready_for_missing_azure_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["dataset"]["ok"] is True
    assert payload["checks"]["llm"]["ok"] is False
    assert "Missing config" in payload["checks"]["llm"]["detail"]


def test_ready_endpoint_reports_ready_for_installed_ollama_model(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "qwen2:0.5b"}]}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2:0.5b")
    get_settings.cache_clear()
    monkeypatch.setattr(main_module.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(health_module.httpx, "AsyncClient", _FakeAsyncClient)

    app = create_app()
    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["dataset"]["ok"] is True
    assert payload["checks"]["llm"]["ok"] is True


def test_anomalies_support_pagination_query_params(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_anomaly_service] = lambda: StubAnomalyService()
    app.dependency_overrides[get_llm_service] = lambda: StubLLMService()
    client = TestClient(app)

    response = client.get("/anomalies?offset=0&limit=1")
    body = response.json()
    assert response.status_code == 200
    assert body["offset"] == 0
    assert body["limit"] == 1
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_audit_report_job_endpoints(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("API_KEYS", '{"admin-key":"admin"}')
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_anomaly_service] = lambda: StubAnomalyService()
    app.dependency_overrides[get_llm_service] = lambda: StubLLMService()
    client = TestClient(app)

    create_resp = client.post("/audit-report/jobs", headers={"x-api-key": "admin-key"}, json={"max_transactions": 10})
    assert create_resp.status_code == 202
    payload = create_resp.json()
    assert payload["job_id"]

    status_resp = client.get(f"/audit-report/jobs/{payload['job_id']}", headers={"x-api-key": "admin-key"})
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] in {"pending", "running", "completed"}


def test_get_anomaly_by_transaction_id_found():
    client = _build_client()
    response = client.get("/anomaly/T100")

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "T100"


def test_get_anomaly_by_transaction_id_not_found():
    client = _build_client()
    response = client.get("/anomaly/T404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


def test_explain_by_transaction_id_success():
    client = _build_client()
    response = client.post("/explain", json={"transaction_id": "T100"})

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "T100"
    assert body["risk_level"] == "High"


def test_explain_transaction_not_found_for_transaction_id():
    client = _build_client()
    response = client.post("/explain", json={"transaction_id": "T999"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


def test_explain_returns_502_on_llm_runtime_error(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_anomaly_service] = lambda: StubAnomalyService()
    app.dependency_overrides[get_llm_service] = lambda: StubLLMErrorService()
    client = TestClient(app)

    response = client.post("/explain", json={"transaction_id": "T100"})
    assert response.status_code == 502
    assert "LLM service error" in response.json()["detail"]


def test_chat_success():
    client = _build_client()
    response = client.post("/chat", json={"question": "What is the top risk?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Answer"


def test_chat_returns_502_on_llm_runtime_error(monkeypatch):
    metrics_store.reset()
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_anomaly_service] = lambda: StubAnomalyService()
    app.dependency_overrides[get_llm_service] = lambda: StubLLMErrorService()
    client = TestClient(app)

    response = client.post("/chat", json={"question": "Risk summary?"})
    assert response.status_code == 502
    assert "LLM service error" in response.json()["detail"]


def test_startup_ollama_model_check_passes_when_model_installed(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "qwen2:0.5b"}]}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2:0.5b")
    get_settings.cache_clear()
    monkeypatch.setattr(main_module.httpx, "AsyncClient", _FakeAsyncClient)

    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_startup_ollama_model_check_fails_when_model_missing(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "qwen2:0.5b"}]}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")
    get_settings.cache_clear()
    monkeypatch.setattr(main_module.httpx, "AsyncClient", _FakeAsyncClient)

    app = create_app()
    with pytest.raises(RuntimeError, match="is not installed"):
        with TestClient(app):
            pass
