from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import (
    AccountBalance,
    ReconciliationRequest,
    ReconciliationSummary,
)
from backend.services.reconciliation_service import (
    ReconciliationService,
    get_reconciliation_service,
)

router = APIRouter()


@router.get("/reconciliation/summary", response_model=ReconciliationSummary)
async def get_reconciliation_summary(
    account_filter: str | None = None,
    currency_filter: str | None = None,
    variance_threshold: float = 0.01,
    include_balanced: bool = True,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationSummary:
    """
    Generate a comprehensive reconciliation summary with variance analysis.
    
    - **account_filter**: Filter accounts containing this string
    - **currency_filter**: Filter by specific currency code
    - **variance_threshold**: Minimum variance to flag as issue (default: 0.01)
    - **include_balanced**: Include accounts with balanced currencies (default: true)
    """
    request = ReconciliationRequest(
        account_filter=account_filter,
        currency_filter=currency_filter,
        variance_threshold=variance_threshold,
        include_balanced=include_balanced,
    )
    return await service.get_summary(request)


@router.get("/reconciliation/balances", response_model=list[AccountBalance])
async def get_account_balances(
    account_filter: str | None = None,
    currency_filter: str | None = None,
    variance_threshold: float = 0.01,
    include_balanced: bool = True,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[AccountBalance]:
    """
    Get detailed account balances with variance analysis.
    
    Returns account balances sorted by variance amount (highest first).
    """
    request = ReconciliationRequest(
        account_filter=account_filter,
        currency_filter=currency_filter,
        variance_threshold=variance_threshold,
        include_balanced=include_balanced,
    )
    return await service.get_account_balances(request)


@router.get("/reconciliation/account/{account}")
async def validate_account_integrity(
    account: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> dict:
    """
    Validate the integrity of a specific account's transactions.
    
    Checks for duplicates, posting key consistency, and balance metrics.
    """
    if not account.strip():
        raise HTTPException(status_code=400, detail="Account parameter cannot be empty")
    
    result = await service.validate_account_integrity(account.strip())
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result