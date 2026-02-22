from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.anomaly_service import AnomalyService, get_anomaly_service
from backend.services.llm_service import LLMService, get_llm_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_audit_assistant(
    request: ChatRequest,
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    anomalies = await anomaly_service.list_anomalies()
    try:
        answer = await llm_service.chat_with_ledger(
            question=request.question,
            anomalies=anomalies,
            max_rows=request.max_transactions,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    return ChatResponse(answer=answer)
