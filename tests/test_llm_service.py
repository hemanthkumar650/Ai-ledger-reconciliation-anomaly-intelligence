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
