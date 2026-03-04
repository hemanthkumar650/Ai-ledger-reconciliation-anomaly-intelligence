import argparse
import sys
import time
from typing import Any

import httpx


def _headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _fail(message: str) -> None:
    print(f"[ERROR] {message}")
    sys.exit(1)


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    api_key: str | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    response = client.request(method, path, headers=_headers(api_key), json=json)
    if response.status_code >= 400:
        _fail(f"{method} {path} failed ({response.status_code}): {response.text}")
    return response.json()


def run_flow(base_url: str, api_key: str | None, question: str) -> None:
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        health = _request(client, "GET", "/health")
        print(f"[OK] Health: {health}")

        anomalies = _request(client, "GET", "/anomalies?offset=0&limit=5", api_key=api_key)
        items = anomalies.get("items", [])
        if not items:
            _fail("No anomalies found; cannot continue demo flow.")
        first = items[0]
        tx_id = first["transaction_id"]
        print(f"[OK] Pulled {len(items)} anomalies, first transaction_id={tx_id}")

        explanation = _request(
            client,
            "POST",
            "/explain",
            api_key=api_key,
            json={"transaction_id": tx_id},
        )
        print(f"[OK] Explain: risk={explanation['risk_level']}, cause={explanation['possible_cause']}")

        chat = _request(
            client,
            "POST",
            "/chat",
            api_key=api_key,
            json={"question": question, "max_transactions": 20},
        )
        print(f"[OK] Chat: {chat['answer'][:200]}")

        job = _request(
            client,
            "POST",
            "/audit-report/jobs",
            api_key=api_key,
            json={"max_transactions": 25},
        )
        job_id = job["job_id"]
        print(f"[OK] Created report job_id={job_id}")

        for _ in range(20):
            status = _request(client, "GET", f"/audit-report/jobs/{job_id}", api_key=api_key)
            if status["status"] in {"completed", "failed"}:
                print(f"[OK] Job status={status['status']}")
                if status["status"] == "completed":
                    result = status.get("result") or {}
                    print(
                        "[OK] Report totals: "
                        f"flagged={result.get('total_flagged')} high={result.get('high_risk')} "
                        f"medium={result.get('medium_risk')} low={result.get('low_risk')}"
                    )
                    return
                _fail(f"Report job failed: {status.get('error')}")
            time.sleep(0.5)

    _fail("Timed out waiting for report job completion.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an end-to-end AuditAI API flow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="AuditAI API base URL")
    parser.add_argument("--api-key", default=None, help="Optional x-api-key header value")
    parser.add_argument(
        "--question",
        default="What are the top risk patterns in the current flagged transactions?",
        help="Question for /chat endpoint",
    )
    args = parser.parse_args()
    run_flow(args.base_url, args.api_key, args.question)


if __name__ == "__main__":
    main()
