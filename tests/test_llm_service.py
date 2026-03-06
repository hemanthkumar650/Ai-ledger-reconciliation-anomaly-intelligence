import asyncio

import backend.services.llm_service as llm_module
import httpx
from backend.models.schemas import AnomalyResponse
from backend.services.llm_service import LLMService
from backend.utils.config import Settings


def test_build_user_prompt_redacts_sensitive_fields():
    service = LLMService(Settings(llm_provider="ollama"))
    anomaly = AnomalyResponse(
        transaction_id="X1",
        amount=10.0,
        account="4000",
        anomaly_score=0.9,
        risk_level="High",
        metadata={"vendor_email": "vendor@example.com", "iban_number": "DE123456"},
    )

    prompt = service._build_user_prompt(anomaly)

    assert "vendor@example.com" not in prompt
    assert "DE123456" not in prompt
    assert "[REDACTED]" in prompt


def test_normalize_output_falls_back_to_medium_for_invalid_risk():
    payload = {"risk_level": "critical", "explanation": "x", "possible_cause": "y", "recommended_action": "z"}

    normalized = LLMService._normalize_output(payload)

    assert normalized["risk_level"] == "Medium"


def test_build_dataset_context_respects_max_rows():
    rows = [
        AnomalyResponse(transaction_id="A1", amount=10.0, account="4000", anomaly_score=0.9, risk_level="High"),
        AnomalyResponse(transaction_id="A2", amount=20.0, account="5000", anomaly_score=0.7, risk_level="Medium"),
    ]

    context = LLMService._build_dataset_context(rows, max_rows=1)

    assert "A1" in context
    assert "A2" not in context


def test_sanitize_payload_handles_nested_sensitive_fields():
    payload = {"vendor": {"bank_account": "123"}, "contacts": [{"email": "a@b.com"}]}

    sanitized = LLMService._sanitize_payload(payload)

    assert sanitized["vendor"]["bank_account"] == "[REDACTED]"
    assert sanitized["contacts"][0]["email"] == "[REDACTED]"


def test_with_retries_recovers_after_timeouts(monkeypatch):
    class DummyTimeout(Exception):
        pass

    monkeypatch.setattr(llm_module, "APITimeoutError", DummyTimeout)

    service = LLMService(Settings(llm_provider="ollama"))
    anomaly = AnomalyResponse(
        transaction_id="X2",
        amount=10.0,
        account="4000",
        anomaly_score=0.9,
        risk_level="High",
    )

    attempts = {"count": 0}

    async def fake_fn(_anomaly):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise DummyTimeout("timeout")
        return {"explanation": "ok", "risk_level": "High", "possible_cause": "c", "recommended_action": "a"}

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)

    result = asyncio.run(service._with_retries(fake_fn, anomaly))

    assert attempts["count"] == 3
    assert result["explanation"] == "ok"


def test_with_retries_raises_after_exhausted_timeouts(monkeypatch):
    class DummyTimeout(Exception):
        pass

    monkeypatch.setattr(llm_module, "APITimeoutError", DummyTimeout)

    service = LLMService(Settings(llm_provider="ollama"))
    anomaly = AnomalyResponse(
        transaction_id="X3",
        amount=11.0,
        account="4000",
        anomaly_score=0.8,
        risk_level="Medium",
    )

    async def always_timeout(_anomaly):
        raise DummyTimeout("timeout")

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(service._with_retries(always_timeout, anomaly))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "failed after retries" in str(exc)


def test_with_retries_wraps_api_error(monkeypatch):
    class DummyApiError(Exception):
        pass

    monkeypatch.setattr(llm_module, "APIError", DummyApiError)

    service = LLMService(Settings(llm_provider="ollama"))
    anomaly = AnomalyResponse(
        transaction_id="X4",
        amount=12.0,
        account="4000",
        anomaly_score=0.7,
        risk_level="Medium",
    )

    async def api_error(_anomaly):
        raise DummyApiError("api down")

    try:
        asyncio.run(service._with_retries(api_error, anomaly))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "LLM API error" in str(exc)


def test_explain_anomaly_rejects_unsupported_provider():
    service = LLMService(Settings(llm_provider="unsupported-provider"))
    anomaly = AnomalyResponse(
        transaction_id="X5",
        amount=10.0,
        account="4000",
        anomaly_score=0.9,
        risk_level="High",
    )

    try:
        asyncio.run(service.explain_anomaly(anomaly))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Unsupported LLM provider" in str(exc)


def test_text_completion_dispatches_to_provider_methods(monkeypatch):
    azure = LLMService(Settings(llm_provider="azure"))
    ollama = LLMService(Settings(llm_provider="ollama"))

    async def fake_azure(_system, _user):
        return "azure response"

    async def fake_ollama(_system, _user):
        return "ollama response"

    monkeypatch.setattr(azure, "_text_with_azure", fake_azure)
    monkeypatch.setattr(ollama, "_text_with_ollama", fake_ollama)

    azure_result = asyncio.run(azure._text_completion("s", "u"))
    ollama_result = asyncio.run(ollama._text_completion("s", "u"))

    assert azure_result == "azure response"
    assert ollama_result == "ollama response"


def test_text_completion_rejects_unsupported_provider():
    service = LLMService(Settings(llm_provider="invalid-provider"))

    try:
        asyncio.run(service._text_completion("sys", "usr"))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Unsupported LLM provider" in str(exc)


def test_explain_with_ollama_wraps_http_errors(monkeypatch):
    service = LLMService(Settings(llm_provider="ollama"))
    anomaly = AnomalyResponse(
        transaction_id="X6",
        amount=10.0,
        account="4000",
        anomaly_score=0.9,
        risk_level="High",
    )

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(llm_module.httpx, "AsyncClient", DummyAsyncClient)

    try:
        asyncio.run(service._explain_with_ollama(anomaly))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "LLM API error" in str(exc)


def test_text_with_ollama_wraps_http_errors(monkeypatch):
    service = LLMService(Settings(llm_provider="ollama"))

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(llm_module.httpx, "AsyncClient", DummyAsyncClient)

    try:
        asyncio.run(service._text_with_ollama("sys", "usr"))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "LLM API error" in str(exc)
