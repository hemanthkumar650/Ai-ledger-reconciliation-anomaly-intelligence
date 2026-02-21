from __future__ import annotations

import asyncio
from pathlib import Path

import pandas as pd

from backend.models.schemas import AnomalyResponse
from backend.utils.config import get_settings


class AnomalyService:
    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)

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

    @staticmethod
    def _to_model(row: dict) -> AnomalyResponse:
        label = str(row.get("label", "")).lower()
        risk_from_label = {"global": "High", "local": "Medium", "regular": "Low"}
        score_from_label = {"global": 0.95, "local": 0.75, "regular": 0.05}

        return AnomalyResponse(
            transaction_id=AnomalyService._row_transaction_id(row),
            amount=float(row.get("amount", row.get("DMBTR", 0.0))),
            account=str(row.get("account", row.get("HKONT", "unknown"))),
            anomaly_score=float(row.get("anomaly_score", score_from_label.get(label, 0.5))),
            risk_level=str(row.get("risk_level", risk_from_label.get(label, "Unknown"))),
            metadata={k: v for k, v in row.items() if k not in {"transaction_id", "amount", "account", "anomaly_score", "risk_level"}},
        )

    @staticmethod
    def _row_transaction_id(row: dict) -> str:
        return str(row.get("transaction_id", row.get("BELNR", "")))


def get_anomaly_service() -> AnomalyService:
    settings = get_settings()
    return AnomalyService(csv_path=settings.anomalies_csv_path)
