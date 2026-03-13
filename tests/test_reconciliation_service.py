import pytest
from unittest.mock import patch

from backend.models.schemas import ReconciliationRequest
from backend.services.reconciliation_service import ReconciliationService


@pytest.fixture
def sample_ledger_data():
    """Sample ledger data for testing."""
    return [
        {
            "BELNR": "100001",
            "WAERS": "USD",
            "BUKRS": "C01",
            "KTOSL": "C1",
            "PRCTR": "P01",
            "BSCHL": "A1",
            "HKONT": "A001",
            "DMBTR": 1000.0,
            "WRBTR": 1000.0,
        },
        {
            "BELNR": "100002",
            "WAERS": "USD",
            "BUKRS": "C01",
            "KTOSL": "C1",
            "PRCTR": "P01",
            "BSCHL": "A1",
            "HKONT": "A001",
            "DMBTR": -500.0,
            "WRBTR": -500.0,
        },
        {
            "BELNR": "100003",
            "WAERS": "EUR",
            "BUKRS": "C02",
            "KTOSL": "C2",
            "PRCTR": "P02",
            "BSCHL": "A2",
            "HKONT": "A002",
            "DMBTR": 2000.0,
            "WRBTR": 1800.0,
        },
        {
            "BELNR": "100004",
            "WAERS": "USD",
            "BUKRS": "C01",
            "KTOSL": "C1",
            "PRCTR": "P01",
            "BSCHL": "A1",
            "HKONT": "A003",
            "DMBTR": 5000.0,
            "WRBTR": 0.0,
        },
    ]


@pytest.fixture
def reconciliation_service():
    """ReconciliationService fixture with mocked CSV path."""
    return ReconciliationService(csv_path="/fake/path.csv")


@pytest.mark.asyncio
async def test_get_summary_basic(reconciliation_service, sample_ledger_data):
    """Test basic reconciliation summary functionality."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        summary = await reconciliation_service.get_summary()

    assert summary.total_accounts == 3
    assert summary.unbalanced_accounts > 0
    assert len(summary.issues) > 0
    assert 0 <= summary.completion_percentage <= 100
    assert summary.last_reconciled


@pytest.mark.asyncio
async def test_get_account_balances(reconciliation_service, sample_ledger_data):
    """Test account balance calculation."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        balances = await reconciliation_service.get_account_balances()

    assert len(balances) == 3

    a001_balance = next((b for b in balances if b.account == "A001"), None)
    assert a001_balance is not None
    assert a001_balance.local_balance == 500.0
    assert a001_balance.doc_balance == 500.0
    assert a001_balance.variance == 0.0

    a002_balance = next((b for b in balances if b.account == "A002"), None)
    assert a002_balance is not None
    assert a002_balance.local_balance == 2000.0
    assert a002_balance.doc_balance == 1800.0
    assert a002_balance.variance == 200.0


@pytest.mark.asyncio
async def test_get_account_balances_with_filters(reconciliation_service, sample_ledger_data):
    """Test account balance filtering."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        balances = await reconciliation_service.get_account_balances(
            ReconciliationRequest(currency_filter="USD")
        )

    assert len(balances) == 2
    assert {b.currency for b in balances} == {"USD"}

    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        balances = await reconciliation_service.get_account_balances(
            ReconciliationRequest(account_filter="A001")
        )

    assert len(balances) == 1
    assert balances[0].account == "A001"


@pytest.mark.asyncio
async def test_validate_account_integrity(reconciliation_service, sample_ledger_data):
    """Test account integrity validation."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        result = await reconciliation_service.validate_account_integrity("A001")

    assert result["status"] == "ok"
    assert result["account"] == "A001"
    assert result["transaction_count"] == 2
    assert result["local_currency_total"] == 500.0
    assert result["document_currency_total"] == 500.0
    assert result["balance_variance"] == 0.0
    assert "USD" in result["currencies_used"]

    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        result = await reconciliation_service.validate_account_integrity("NONEXISTENT")

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_detect_reconciliation_issues(reconciliation_service, sample_ledger_data):
    """Test reconciliation issue detection."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        balances = await reconciliation_service.get_account_balances()

    issues = reconciliation_service._detect_reconciliation_issues(
        balances,
        sample_ledger_data,
        ReconciliationRequest(variance_threshold=0.01),
    )

    assert len(issues) >= 2
    assert len([issue for issue in issues if issue.issue_type == "balance_variance"]) >= 1
    assert len([issue for issue in issues if issue.issue_type == "missing_document_currency"]) >= 1


def test_load_ledger_data_file_not_exists(reconciliation_service):
    """Test loading data when CSV file doesn't exist."""
    data = reconciliation_service._load_ledger_data()
    assert data == []


@pytest.mark.parametrize(
    "variance_threshold,expected_balanced",
    [
        (0.01, 1),
        (200.0, 2),
        (5000.0, 3),
    ],
)
@pytest.mark.asyncio
async def test_variance_threshold_logic(
    reconciliation_service,
    sample_ledger_data,
    variance_threshold,
    expected_balanced,
):
    """Test variance threshold logic with different values."""
    with patch.object(reconciliation_service, "_load_ledger_data", return_value=sample_ledger_data):
        summary = await reconciliation_service.get_summary(
            ReconciliationRequest(variance_threshold=variance_threshold)
        )

    assert summary.balanced_accounts == expected_balanced
