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
