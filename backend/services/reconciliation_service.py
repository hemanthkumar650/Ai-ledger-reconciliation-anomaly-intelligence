from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.models.schemas import (
    AccountBalance,
    ReconciliationIssue,
    ReconciliationRequest,
    ReconciliationSummary,
)
from backend.utils.config import get_settings


class ReconciliationService:
    """Financial reconciliation service for ledger analysis and balance verification."""

    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)

    async def get_summary(self, request: ReconciliationRequest | None = None) -> ReconciliationSummary:
        """Generate comprehensive reconciliation summary with variance analysis."""
        if request is None:
            request = ReconciliationRequest()
        
        rows = await asyncio.to_thread(self._load_ledger_data)
        balances = await asyncio.to_thread(self._calculate_account_balances, rows, request)
        issues = await asyncio.to_thread(self._detect_reconciliation_issues, balances, rows, request)
        
        total_accounts = len(balances)
        balanced_accounts = sum(1 for b in balances if abs(b.variance) <= request.variance_threshold)
        total_variance = sum(abs(b.variance) for b in balances)
        completion_percentage = (balanced_accounts / total_accounts * 100) if total_accounts > 0 else 0.0
        
        return ReconciliationSummary(
            total_accounts=total_accounts,
            balanced_accounts=balanced_accounts,
            unbalanced_accounts=total_accounts - balanced_accounts,
            total_variance=round(total_variance, 2),
            issues=issues,
            completion_percentage=round(completion_percentage, 2),
            last_reconciled=datetime.now().isoformat(),
        )

    async def get_account_balances(self, request: ReconciliationRequest | None = None) -> list[AccountBalance]:
        """Get detailed account balances with variance analysis."""
        if request is None:
            request = ReconciliationRequest()
            
        rows = await asyncio.to_thread(self._load_ledger_data)
        return await asyncio.to_thread(self._calculate_account_balances, rows, request)

    async def validate_account_integrity(self, account: str) -> dict[str, Any]:
        """Validate integrity of a specific account's transactions."""
        rows = await asyncio.to_thread(self._load_ledger_data)
        account_transactions = [row for row in rows if row.get('HKONT') == account]
        
        if not account_transactions:
            return {"status": "error", "message": f"Account {account} not found"}
        
        # Check for duplicate transactions
        doc_numbers = [tx.get('BELNR') for tx in account_transactions]
        duplicates = [doc for doc in set(doc_numbers) if doc_numbers.count(doc) > 1]
        
        # Check posting key consistency
        posting_keys = set(tx.get('BSCHL') for tx in account_transactions)
        
        # Calculate balance metrics
        local_total = sum(float(tx.get('DMBTR', 0)) for tx in account_transactions)
        doc_total = sum(float(tx.get('WRBTR', 0)) for tx in account_transactions)
        
        return {
            "status": "ok",
            "account": account,
            "transaction_count": len(account_transactions),
            "duplicate_documents": len(duplicates),
            "posting_key_variety": len(posting_keys),
            "local_currency_total": round(local_total, 2),
            "document_currency_total": round(doc_total, 2),
            "balance_variance": round(abs(local_total - doc_total), 2),
            "currencies_used": sorted({tx.get('WAERS') for tx in account_transactions}),
        }

    def _load_ledger_data(self) -> list[dict]:
        """Load and validate ledger data from CSV."""
        if not self.csv_path.exists():
            return []
        
        try:
            df = pd.read_csv(self.csv_path)
            return df.to_dict('records')
        except Exception:
            return []

    def _calculate_account_balances(self, rows: list[dict], request: ReconciliationRequest) -> list[AccountBalance]:
        """Calculate account balances grouped by account and currency."""
        # Group by account and currency  
        account_groups = defaultdict(lambda: defaultdict(list))
        
        for row in rows:
            account = str(row.get('HKONT', '')).strip()
            currency = str(row.get('WAERS', '')).strip()
            
            # Apply filters
            if request.account_filter and request.account_filter not in account:
                continue
            if request.currency_filter and currency != request.currency_filter:
                continue
                
            account_groups[account][currency].append(row)
        
        balances = []
        for account, currencies in account_groups.items():
            for currency, transactions in currencies.items():
                local_balance = sum(float(tx.get('DMBTR', 0)) for tx in transactions)
                doc_balance = sum(float(tx.get('WRBTR', 0)) for tx in transactions)
                variance = local_balance - doc_balance
                
                # Only include if variance exceeds threshold or if including balanced accounts
                if request.include_balanced or abs(variance) > request.variance_threshold:
                    balances.append(AccountBalance(
                        account=account,
                        local_balance=round(local_balance, 2),
                        doc_balance=round(doc_balance, 2), 
                        transaction_count=len(transactions),
                        currency=currency,
                        variance=round(variance, 2),
                    ))
        
        return sorted(balances, key=lambda x: abs(x.variance), reverse=True)

    def _detect_reconciliation_issues(self, balances: list[AccountBalance], rows: list[dict], request: ReconciliationRequest) -> list[ReconciliationIssue]:
        """Detect various reconciliation issues in the ledger data."""
        issues = []
        
        # 1. Significant balance variances
        for balance in balances:
            if abs(balance.variance) > request.variance_threshold:
                severity = "High" if abs(balance.variance) > 1000 else "Medium" if abs(balance.variance) > 100 else "Low"
                issues.append(ReconciliationIssue(
                    issue_type="balance_variance",
                    severity=severity,
                    account=balance.account,
                    description=f"Currency balance variance of {abs(balance.variance):.2f} detected",
                    amount=balance.variance,
                ))
        
        # 2. Accounts with zero document currency but non-zero local currency
        zero_doc_accounts = [b for b in balances if b.doc_balance == 0 and b.local_balance != 0]
        for balance in zero_doc_accounts:
            issues.append(ReconciliationIssue(
                issue_type="missing_document_currency",
                severity="High",
                account=balance.account,
                description=f"Account has local currency balance ({balance.local_balance:.2f}) but zero document currency",
                amount=balance.local_balance,
            ))
        
        # 3. Detect potential duplicate transactions
        doc_number_counts = defaultdict(list)
        for row in rows:
            doc_num = str(row.get('BELNR', '')).strip()
            if doc_num:
                doc_number_counts[doc_num].append(row)
        
        duplicates = {doc: rows for doc, rows in doc_number_counts.items() if len(rows) > 2}  # More than 2 entries might indicate issues
        if duplicates:
            issues.append(ReconciliationIssue(
                issue_type="potential_duplicates",
                severity="Medium",
                description=f"Found {len(duplicates)} document numbers with multiple entries (potential duplicates)",
                transaction_ids=list(duplicates.keys())[:10],  # Limit to first 10
            ))
        
        # 4. Accounts with unusually low transaction counts
        low_activity_accounts = [b for b in balances if b.transaction_count == 1 and abs(b.local_balance) > 10000]
        if low_activity_accounts:
            issues.append(ReconciliationIssue(
                issue_type="low_activity_high_balance",
                severity="Medium", 
                description=f"Found {len(low_activity_accounts)} accounts with single high-value transactions",
            ))
        
        return sorted(issues, key=lambda x: {"High": 3, "Medium": 2, "Low": 1}[x.severity], reverse=True)


def get_reconciliation_service() -> ReconciliationService:
    """Dependency provider for ReconciliationService."""
    settings = get_settings()
    return ReconciliationService(csv_path=settings.anomalies_csv_path)
