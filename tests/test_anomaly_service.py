import asyncio

from backend.services.anomaly_service import AnomalyService


def test_anomaly_service_filters_regular_rows(tmp_path):
    csv_path = tmp_path / "anomalies.csv"
    csv_path.write_text(
        "BELNR,amount,HKONT,label\n"
        "1001,1000.0,4000,regular\n"
        "1002,2500.0,5000,local\n"
        "1003,5000.0,6000,global\n",
        encoding="utf-8",
    )

    service = AnomalyService(str(csv_path))
    rows = asyncio.run(service.list_anomalies())

    assert len(rows) == 2
    assert {row.transaction_id for row in rows} == {"1002", "1003"}


def test_get_by_transaction_id_found_and_missing(tmp_path):
    csv_path = tmp_path / "anomalies.csv"
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
    assert missing is None


def test_account_score_override_updates_score_and_risk(tmp_path):
    csv_path = tmp_path / "anomalies.csv"
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


def test_category_score_override_applies_when_account_override_missing(tmp_path):
    csv_path = tmp_path / "anomalies.csv"
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
