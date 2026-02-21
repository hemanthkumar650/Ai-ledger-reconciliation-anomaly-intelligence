from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import AnomalyListResponse, AnomalyResponse
from backend.services.anomaly_service import AnomalyService, get_anomaly_service

router = APIRouter()


@router.get("/anomalies", response_model=AnomalyListResponse)
async def list_anomalies(service: AnomalyService = Depends(get_anomaly_service)) -> AnomalyListResponse:
    anomalies = await service.list_anomalies()
    return AnomalyListResponse(total=len(anomalies), items=anomalies)


@router.get("/anomaly/{transaction_id}", response_model=AnomalyResponse)
async def get_anomaly(
    transaction_id: str,
    service: AnomalyService = Depends(get_anomaly_service),
) -> AnomalyResponse:
    anomaly = await service.get_by_transaction_id(transaction_id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return anomaly
