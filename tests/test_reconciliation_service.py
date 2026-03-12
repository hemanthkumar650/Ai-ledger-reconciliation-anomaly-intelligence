import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from backend.services.reconciliation_service import ReconciliationService
from backend.models.schemas import ReconciliationRequest


@pytest.fixture
def sample_ledger_data():
    """Sample ledger data for testing."""
    return [
        {
            'BELNR': '100001', 'WAERS': 'USD', 'BUKRS': 'C01', 'KTOSL': 'C1', 
            'PRCTR': 'P01', 'BSCHL': 'A1', 'HKONT': 'A001', 'DMBTR': 1000.0, 'WRBTR': 1000.0
        },
        {
            'BELNR': '100002', 'WAERS': 'USD', 'BUKRS': 'C01', 'KTOSL': 'C1',
            'PRCTR': 'P01', 'BSCHL': 'A1', 'HKONT': 'A001', 'DMBTR': -500.0, 'WRBTR': -500.0
        },
        {
            'BELNR': '100003', 'WAERS': 'EUR', 'BUKRS': 'C02', 'KTOSL': 'C2',
            'PRCTR': 'P02', 'BSCHL': 'A2', 'HKONT': 'A002', 'DMBTR': 2000.0, 'WRBTR': 1800.0  # Variance
        },
        {
            'BELNR': '100004', 'WAERS': 'USD', 'BUKRS': 'C01', 'KTOSL': 'C1',
            'PRCTR': 'P01', 'BSCHL': 'A1', 'HKONT': 'A003', 'DMBTR': 5000.0, 'WRBTR': 0.0  # Missing doc currency
        },
    ]


@pytest.fixture
def reconciliation_service():
    """ReconciliationService fixture with mocked CSV path."""
    return ReconciliationService(csv_path="/fake/path.csv")


@pytest.mark.asyncio
async def test_get_summary_basic(reconciliation_service, sample_ledger_data):
    """Test basic reconciliation summary functionality."""
    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):
        summary = await reconciliation_service.get_summary()
        
        assert summary.total_accounts == 3  # A001, A002, A003
        assert summary.unbalanced_accounts > 0  # At least A002 and A003 should be unbalanced
        assert len(summary.issues) > 0
        assert 0 <= summary.completion_percentage <= 100
        assert summary.last_reconciled\n\n\n@pytest.mark.asyncio\nasync def test_get_account_balances(reconciliation_service, sample_ledger_data):\n    \"\"\"Test account balance calculation.\"\"\"\n    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):\n        balances = await reconciliation_service.get_account_balances()\n        \n        # Should have balances for all 3 accounts\n        assert len(balances) == 3\n        \n        # Check A001 balance (USD): 1000 + (-500) = 500 for both currencies\n        a001_balance = next((b for b in balances if b.account == 'A001'), None)\n        assert a001_balance is not None\n        assert a001_balance.local_balance == 500.0\n        assert a001_balance.doc_balance == 500.0\n        assert a001_balance.variance == 0.0\n        \n        # Check A002 balance (EUR): has variance\n        a002_balance = next((b for b in balances if b.account == 'A002'), None)\n        assert a002_balance is not None\n        assert a002_balance.local_balance == 2000.0\n        assert a002_balance.doc_balance == 1800.0\n        assert a002_balance.variance == 200.0\n\n\n@pytest.mark.asyncio\nasync def test_get_account_balances_with_filters(reconciliation_service, sample_ledger_data):\n    \"\"\"Test account balance filtering.\"\"\"\n    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):\n        # Filter by currency\n        request = ReconciliationRequest(currency_filter='USD')\n        balances = await reconciliation_service.get_account_balances(request)\n        \n        # Should only have USD accounts (A001 and A003)\n        assert len(balances) == 2\n        currencies = {b.currency for b in balances}\n        assert currencies == {'USD'}\n        \n        # Filter by account\n        request = ReconciliationRequest(account_filter='A001')\n        balances = await reconciliation_service.get_account_balances(request)\n        \n        assert len(balances) == 1\n        assert balances[0].account == 'A001'\n\n\n@pytest.mark.asyncio\nasync def test_validate_account_integrity(reconciliation_service, sample_ledger_data):\n    \"\"\"Test account integrity validation.\"\"\"\n    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):\n        # Test existing account\n        result = await reconciliation_service.validate_account_integrity('A001')\n        \n        assert result['status'] == 'ok'\n        assert result['account'] == 'A001'\n        assert result['transaction_count'] == 2  # Two transactions for A001\n        assert result['local_currency_total'] == 500.0\n        assert result['document_currency_total'] == 500.0\n        assert result['balance_variance'] == 0.0\n        assert 'USD' in result['currencies_used']\n        \n        # Test non-existent account\n        result = await reconciliation_service.validate_account_integrity('NONEXISTENT')\n        \n        assert result['status'] == 'error'\n        assert 'not found' in result['message'].lower()\n\n\n@pytest.mark.asyncio\nasync def test_detect_reconciliation_issues(reconciliation_service, sample_ledger_data):\n    \"\"\"Test reconciliation issue detection.\"\"\"\n    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):\n        balances = await reconciliation_service.get_account_balances()\n        request = ReconciliationRequest(variance_threshold=0.01)\n        \n        issues = reconciliation_service._detect_reconciliation_issues(balances, sample_ledger_data, request)\n        \n        # Should detect at least the variance issue in A002 and missing doc currency in A003\n        assert len(issues) >= 2\n        \n        # Check for balance variance issue\n        variance_issues = [i for i in issues if i.issue_type == 'balance_variance']\n        assert len(variance_issues) >= 1\n        \n        # Check for missing document currency issue\n        missing_doc_issues = [i for i in issues if i.issue_type == 'missing_document_currency']\n        assert len(missing_doc_issues) >= 1\n\n\ndef test_load_ledger_data_file_not_exists(reconciliation_service):\n    \"\"\"Test loading data when CSV file doesn't exist.\"\"\"\n    # Service is initialized with fake path, so file won't exist\n    data = reconciliation_service._load_ledger_data()\n    assert data == []\n\n\n@pytest.mark.parametrize(\"variance_threshold,expected_balanced\", [\n    (0.01, 1),  # Only A001 should be balanced (variance = 0)\n    (200.0, 2),  # A001 and A002 should be balanced (A002 variance = 200)\n    (5000.0, 3), # All accounts should be balanced\n])\n@pytest.mark.asyncio\nasync def test_variance_threshold_logic(reconciliation_service, sample_ledger_data, variance_threshold, expected_balanced):\n    \"\"\"Test variance threshold logic with different values.\"\"\"\n    with patch.object(reconciliation_service, '_load_ledger_data', return_value=sample_ledger_data):\n        request = ReconciliationRequest(variance_threshold=variance_threshold)\n        summary = await reconciliation_service.get_summary(request)\n        \n        assert summary.balanced_accounts == expected_balanced