from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
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
        self.has_label_data = self._csv_has_label_column()
        
        self.ml_model = IsolationForestAnomalyModel(contamination=0.1)
        if not self.has_label_data:
            try:
                self.ml_model.fit(str(self.csv_path))
            except Exception as e:
                logger.warning(f"Failed to train ML model: {e}. Using fallback scoring.")

    async def list_anomalies(self) -> list[AnomalyResponse]:
        return await asyncio.to_thread(self._list_anomalies_sync)

    async def get_by_transaction_id(self, transaction_id: str) -> AnomalyResponse | None:
        return await asyncio.to_thread(self._get_by_transaction_id_sync, transaction_id)

    def _list_anomalies_sync(self) -> list[AnomalyResponse]:
        rows = self._load_rows()
        if self._has_label_column(rows):
            rows = [row for row in rows if self._is_flagged_row(row)]
        return self._rows_to_models(rows)

    def _get_by_transaction_id_sync(self, transaction_id: str) -> AnomalyResponse | None:
        target_id = str(transaction_id)
        rows = self._load_rows()
        for row in rows:
            if self._row_transaction_id(row) == target_id:
                return self._to_model(row)
        return None

    def _load_rows(self) -> list[dict]:
        if not self.csv_path.exists():
            return []
        df = pd.read_csv(self.csv_path)
        return df.to_dict(orient="records")

    def _csv_has_label_column(self) -> bool:
        if not self.csv_path.exists():
            return False
        try:
            header = pd.read_csv(self.csv_path, nrows=1)
        except Exception as exc:
            logger.warning(f"Failed to inspect CSV headers for labels: {exc}")
            return False
        return any(str(column).strip().lower() == "label" for column in header.columns)

    def _rows_to_models(self, rows: list[dict]) -> list[AnomalyResponse]:
        if not rows:
            return []

        amounts = [float(row.get("amount", row.get("DMBTR", 0.0))) for row in rows]
        accounts = [str(row.get("account", row.get("HKONT", "unknown"))).strip() for row in rows]

        if self.ml_model.is_fitted:
            base_scores = self.ml_model.predict_batch(amounts, accounts)
        else:
            base_scores = [0.5] * len(rows)

        anomalies: list[AnomalyResponse] = []
        for row, amount, account, base_score in zip(rows, amounts, accounts, base_scores):
            score, _override_applied = self._resolve_score(row, base_score)
            risk_level = self._score_to_risk_level(score)
            anomalies.append(
                AnomalyResponse(
                    transaction_id=AnomalyService._row_transaction_id(row),
                    amount=amount,
                    account=account,
                    anomaly_score=score,
                    risk_level=risk_level,
                    metadata={
                        k: v
                        for k, v in row.items()
                        if k
                        not in {
                            "transaction_id",
                            "BELNR",
                            "amount",
                            "DMBTR",
                            "account",
                            "HKONT",
                            "anomaly_score",
                            "risk_level",
                        }
                    },
                )
            )

        return anomalies

    @staticmethod
    def _has_label_column(rows: list[dict]) -> bool:
        return bool(rows) and any(str(key).strip().lower() == "label" for key in rows[0].keys())

    @staticmethod
    def _is_flagged_row(row: dict) -> bool:
        label = str(row.get("label", "")).strip().lower()
        return bool(label) and label != "regular"

    def _resolve_score(self, row: dict, fallback_score: float) -> tuple[float, bool]:
        account = str(row.get("account", row.get("HKONT", ""))).strip()
        if account and account in self.account_score_overrides:
            return self.account_score_overrides[account], True

        category_raw = row.get("category", row.get("CATEGORY", row.get("transaction_type", "")))
        category = str(category_raw).strip().lower()
        if category and category in self.category_score_overrides:
            return self.category_score_overrides[category], True

        label = str(row.get("label", "")).strip().lower()
        if label == "global":
            return 0.95, True
        if label == "local":
            return 0.7, True

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
        
        # Use the trained model only for unlabeled datasets.
        base_score = self.ml_model.predict_anomaly_score(amount, account) if self.ml_model.is_fitted else 0.5
        
        # Apply account or category overrides if configured
        score, _override_applied = self._resolve_score(row, base_score)
        
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


@lru_cache
def get_anomaly_service() -> AnomalyService:
    settings = get_settings()
    return AnomalyService(
        csv_path=settings.anomalies_csv_path,
        account_score_overrides=settings.risk_score_by_account,
        category_score_overrides=settings.risk_score_by_category,
        high_cutoff=settings.risk_level_high_cutoff,
        medium_cutoff=settings.risk_level_medium_cutoff,
    )
