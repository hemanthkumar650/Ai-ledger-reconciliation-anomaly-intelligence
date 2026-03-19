from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pandas as pd

from backend.ml.isolation_forest_model import IsolationForestAnomalyModel
from backend.models.schemas import AnomalyResponse
from backend.utils.config import get_settings

logger = logging.getLogger(__name__)


class AnomalyService:
    def __init__(
        self,
        csv_path: str,
        account_score_overrides: dict[str, float] | None = None,
        category_score_overrides: dict[str, float] | None = None,
        high_cutoff: float = 0.85,
        medium_cutoff: float = 0.6,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.account_score_overrides = {
            str(k).strip(): float(v)
            for k, v in (account_score_overrides or {}).items()
            if str(k).strip()
        }
        self.category_score_overrides = {
            str(k).strip().lower(): float(v)
            for k, v in (category_score_overrides or {}).items()
            if str(k).strip()
        }
        self.high_cutoff = float(high_cutoff)
        self.medium_cutoff = float(medium_cutoff)
        
        # Initialize and train ML model
        self.ml_model = IsolationForestAnomalyModel(contamination=0.1)
        try:
            self.ml_model.fit(str(self.csv_path))
        except Exception as e:
            logger.warning(f"Failed to train ML model: {e}. Using fallback scoring.")

    async def list_anomalies(self) -> list[AnomalyResponse]:
        rows = await asyncio.to_thread(self._load_rows)
        return [self._to_model(row) for row in rows]

    async def get_by_transaction_id(self, transaction_id: str) -> AnomalyResponse | None:
        rows = await asyncio.to_thread(self._load_rows)
        for row in rows:
            if self._row_transaction_id(row) == str(transaction_id):
                return self._to_model(row)
        return None

    def _load_rows(self) -> list[dict]:
        if not self.csv_path.exists():
            return []
        df = pd.read_csv(self.csv_path)
        # With ML model scoring, score ALL transactions (not just non-regular ones)
        # The model will determine what's anomalous based on statistical features
        return df.to_dict(orient="records")

    def _resolve_score(self, row: dict, fallback_score: float) -> tuple[float, bool]:
        account = str(row.get("account", row.get("HKONT", ""))).strip()
        if account and account in self.account_score_overrides:
            return self.account_score_overrides[account], True

        category_raw = row.get("category", row.get("CATEGORY", row.get("transaction_type", "")))
        category = str(category_raw).strip().lower()
        if category and category in self.category_score_overrides:
            return self.category_score_overrides[category], True

        return fallback_score, False

    def _score_to_risk_level(self, score: float) -> str:
        if score >= self.high_cutoff:
            return "High"
        if score >= self.medium_cutoff:
            return "Medium"
        return "Low"

    def _to_model(self, row: dict) -> AnomalyResponse:
        # Normalize column names
        amount = float(row.get("amount", row.get("DMBTR", 0.0)))
        account = str(row.get("account", row.get("HKONT", "unknown"))).strip()
        
        # Get base score from ML model
        base_score = self.ml_model.predict_anomaly_score(amount, account)
        
        # Apply account or category overrides if configured
        score, override_applied = self._resolve_score(row, base_score)
        
        # Determine risk level from score
        risk_level = self._score_to_risk_level(score)

        return AnomalyResponse(
            transaction_id=AnomalyService._row_transaction_id(row),
            amount=amount,
            account=account,
            anomaly_score=score,
            risk_level=risk_level,
            metadata={
                k: v
                for k, v in row.items()
                if k not in {"transaction_id", "BELNR", "amount", "DMBTR", "account", "HKONT", "anomaly_score", "risk_level"}
            },
        )

    @staticmethod
    def _row_transaction_id(row: dict) -> str:
        return str(row.get("transaction_id", row.get("BELNR", "")))


def get_anomaly_service() -> AnomalyService:
    settings = get_settings()
    return AnomalyService(
        csv_path=settings.anomalies_csv_path,
        account_score_overrides=settings.risk_score_by_account,
        category_score_overrides=settings.risk_score_by_category,
        high_cutoff=settings.risk_level_high_cutoff,
        medium_cutoff=settings.risk_level_medium_cutoff,
    )
