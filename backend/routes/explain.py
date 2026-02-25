from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import ExplainRequest, ExplainResponse
from backend.services.anomaly_service import AnomalyService, get_anomaly_service
from backend.services.llm_service import LLMService, get_llm_service

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
async def explain_transaction(
    request: ExplainRequest,
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> ExplainResponse:
    # Normalize transaction_id so whitespace-only values are treated as missing.
    transaction_id = request.transaction_id.strip() if request.transaction_id else None
    anomaly = request.transaction

    # If both fields are provided, ensure they refer to the same transaction.
    if anomaly is not None and transaction_id and anomaly.transaction_id != transaction_id:
        raise HTTPException(
            status_code=400,
            detail="transaction_id does not match request.transaction.transaction_id",
        )

    if anomaly is None:
        if not transaction_id:
            raise HTTPException(status_code=400, detail="Provide transaction_id or transaction payload")
        anomaly = await anomaly_service.get_by_transaction_id(transaction_id)
        if not anomaly:
            raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        explanation = await llm_service.explain_anomaly(anomaly)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}") from exc
    return ExplainResponse(transaction_id=anomaly.transaction_id, **explanation)
