import asyncio
from pathlib import Path

from backend.services.anomaly_service import AnomalyService


TEST_DATA_DIR = Path(__file__).resolve().parents[1] / ".tmp" / "test-data"


def _csv_path(name: str) -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_DIR / name


def test_anomaly_service_loads_all_transactions():
    """Test that ML-based service loads all transactions (not just labeled flagged ones)."""
    csv_path = _csv_path("anomaly-service-all-rows.csv")
    csv_path.write_text(
        "BELNR,amount,HKONT,label\n"
        "1001,1000.0,4000,regular\n"
        "1002,2500.0,5000,local\n"
        "1003,5000.0,6000,global\n",
        encoding="utf-8",
    )

    service = AnomalyService(str(csv_path))
    rows = asyncio.run(service.list_anomalies())

    # Should load all 3 transactions (ML model scores them all)
    assert len(rows) == 3
    assert {row.transaction_id for row in rows} == {"1001", "1002", "1003"}


def test_get_by_transaction_id_found_and_missing():
    csv_path = _csv_path("anomaly-service-by-id.csv")
    csv_path.write_text(
        "transaction_id,amount,account,label\n"
        "A1,1200.0,4100,local\n",
        encoding="utf-8",
    )

    service = AnomalyService(str(csv_path))

    found = asyncio.run(service.get_by_transaction_id("A1"))
    missing = asyncio.run(service.get_by_transaction_id("A2"))

    assert found is not None
    assert found.transaction_id == "A1"
    assert found.anomaly_score >= 0.0 and found.anomaly_score <= 1.0
    assert missing is None


def test_account_score_override_updates_score_and_risk():
    csv_path = _csv_path("anomaly-service-account-override.csv")
    csv_path.write_text(
        "transaction_id,amount,account,label\n"
        "A1,1200.0,4100,local\n",
        encoding="utf-8",
    )

    service = AnomalyService(
        str(csv_path),
        account_score_overrides={"4100": 0.95},
        high_cutoff=0.85,
        medium_cutoff=0.6,
    )
    row = asyncio.run(service.get_by_transaction_id("A1"))

    assert row is not None
    assert abs(row.anomaly_score - 0.95) < 1e-9
    assert row.risk_level == "High"


def test_category_score_override_applies_when_account_override_missing():
    csv_path = _csv_path("anomaly-service-category-override.csv")
    csv_path.write_text(
        "transaction_id,amount,account,category,label\n"
        "B1,700.0,5100,travel,local\n",
        encoding="utf-8",
    )

    service = AnomalyService(
        str(csv_path),
        account_score_overrides={"9999": 0.99},
        category_score_overrides={"travel": 0.62},
        high_cutoff=0.85,
        medium_cutoff=0.6,
    )
    row = asyncio.run(service.get_by_transaction_id("B1"))

    assert row is not None
    assert abs(row.anomaly_score - 0.62) < 1e-9
    assert row.risk_level == "Medium"


def test_ml_model_produces_valid_anomaly_scores():
    """Test that ML model produces valid scores between 0.0 and 1.0."""
    csv_path = _csv_path("anomaly-service-ml-scores.csv")
    csv_path.write_text(
        "transaction_id,amount,account\n"
        "T1,100.0,1000\n"
        "T2,50000.0,2000\n"
        "T3,500.0,3000\n"
        "T4,100.0,4000\n",
        encoding="utf-8",
    )

    service = AnomalyService(str(csv_path))
    rows = asyncio.run(service.list_anomalies())

    assert len(rows) == 4
    for row in rows:
        assert 0.0 <= row.anomaly_score <= 1.0, f"Score out of range: {row.anomaly_score}"
        assert row.risk_level in ["Low", "Medium", "High"]


def test_ml_model_detects_statistical_outliers():
    """Test that ML model gives higher scores to statistical outliers."""
    csv_path = _csv_path("anomaly-service-outliers.csv")
    csv_path.write_text(
        "transaction_id,amount,account\n"
        "T1,100.0,1000\n"
        "T2,110.0,1000\n"
        "T3,105.0,1000\n"
        "T4,500000.0,1000\n",  # Extreme outlier
        encoding="utf-8",
    )

    service = AnomalyService(str(csv_path))
    rows = asyncio.run(service.list_anomalies())

    # Find the outlier transaction
    outlier = next(r for r in rows if r.transaction_id == "T4")
    normal_transactions = [r for r in rows if r.transaction_id in ["T1", "T2", "T3"]]
    
    # Outlier should have higher anomaly score than normal ones
    avg_normal_score = sum(r.anomaly_score for r in normal_transactions) / len(normal_transactions)
    assert outlier.anomaly_score > avg_normal_score, \
        f"Outlier score {outlier.anomaly_score} not > avg normal {avg_normal_score}"

