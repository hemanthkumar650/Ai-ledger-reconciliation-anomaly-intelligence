from __future__ import annotations

import asyncio
from pathlib import Path

import pandas as pd

from backend.models.schemas import AnomalyResponse
from backend.utils.config import get_settings


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
        # If dataset has labels (regular/local/global), return only flagged rows.
        if "label" in df.columns:
            df = df[df["label"].astype(str).str.lower() != "regular"]
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
        label = str(row.get("label", "")).lower()
        risk_from_label = {"global": "High", "local": "Medium", "regular": "Low"}
        score_from_label = {"global": 0.95, "local": 0.75, "regular": 0.05}
        base_score = float(row.get("anomaly_score", score_from_label.get(label, 0.5)))
        score, override_applied = self._resolve_score(row, base_score)
        risk_level = str(row.get("risk_level", "")).strip()
        if override_applied:
            risk_level = self._score_to_risk_level(score)
        elif not risk_level:
            risk_level = risk_from_label.get(label, self._score_to_risk_level(score))

        return AnomalyResponse(
            transaction_id=AnomalyService._row_transaction_id(row),
            amount=float(row.get("amount", row.get("DMBTR", 0.0))),
            account=str(row.get("account", row.get("HKONT", "unknown"))),
            anomaly_score=score,
            risk_level=risk_level,
            metadata={
                k: v
                for k, v in row.items()
                if k not in {"transaction_id", "amount", "account", "anomaly_score", "risk_level"}
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
