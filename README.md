# AuditAI: AI-Powered Ledger Reconciliation and Anomaly Intelligence

AuditAI is a backend platform I independently designed and built end-to-end to identify anomalous accounting transactions, explain risk using LLM reasoning, and generate audit-ready insights through APIs.

## What I Built

- FastAPI backend architecture with clear route-service-model separation.
- Secure configuration management with `.env` using Pydantic settings.
- CSV-driven anomaly ingestion and normalization layer.
- LLM integration supporting:
  - Azure OpenAI
  - Ollama (local fallback)
- Resilient LLM handling with retry logic for rate limits and timeouts.
- API suite for health checks, anomaly retrieval, transaction-level explanation, audit report generation, and natural-language Q&A over ledger context.
- Request validation and error handling with explicit `400`, `404`, and `502` responses.

## Architecture

- `backend/main.py`: App bootstrap, metadata, CORS, router wiring.
- `backend/routes/`: API endpoints and HTTP-level error handling.
- `backend/services/anomaly_service.py`: Data loading, filtering, and transaction lookup.
- `backend/services/llm_service.py`: LLM prompting, retries, output normalization, provider switching.
- `backend/models/schemas.py`: Pydantic request/response contracts.
- `backend/utils/config.py`: Environment-driven settings.
- `backend/data/`: Synthetic accounting dataset used by the anomaly layer.

## Implemented APIs

### `GET /health`
Returns service status and active LLM provider.

### `GET /metrics`
Returns in-memory request/latency/error counters and LLM call/retry/failure telemetry.

### `GET /metrics/prometheus`
Returns Prometheus text exposition format for production scraping.

### `GET /anomalies`
Returns all flagged transactions from the dataset.

### `GET /anomaly/{transaction_id}`
Returns one transaction by ID.

### `POST /explain`
Generates LLM-based audit explanation for a transaction.

Accepted input:
- `transaction_id`, or
- full `transaction` payload.

Validation included:
- Trims whitespace-only IDs.
- Ensures `transaction_id` matches `transaction.transaction_id` when both are supplied.

### `POST /audit-report`
Builds a concise audit summary and returns risk distribution counts.

### `POST /chat`
Answers audit questions using ledger transaction context.

## Tech Stack

- Python
- FastAPI
- Pydantic / pydantic-settings
- Pandas
- Azure OpenAI SDK
- Ollama HTTP API
- Uvicorn / Gunicorn

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.template .env
uvicorn backend.main:app --reload --port 8000
```

## Quality Commands (v1.1)

Run these before pushing:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Notes:
- `pytest` enforces coverage for `backend/` with `--cov-fail-under=80` (configured in `pyproject.toml`).
- CI runs the same lint, format, and test gates on pull requests.

## Environment Configuration

Configure `.env` with the following keys:

```env
APP_ENV=dev
CORS_ORIGINS=["http://localhost:5173"]
ANOMALIES_CSV_PATH=backend/data/Synthetic Accounting Financial Dataset.csv

# azure | ollama
LLM_PROVIDER=azure

AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-azure-openai-key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=<your-chat-deployment-name>

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# optional; if set, non-health routes require x-api-key header
API_KEY=
```

## Quick API Examples

### Explain by transaction ID

```json
{
  "transaction_id": "331521"
}
```

### Generate audit report

```json
{
  "max_transactions": 50
}
```

### Ask audit assistant

```json
{
  "question": "What are the top risk patterns in flagged transactions?",
  "max_transactions": 30
}
```

## Deployment Notes

- Backend is deployment-ready for Azure App Service.
- Recommended startup command:

```bash
gunicorn -k uvicorn.workers.UvicornWorker backend.main:app
```

## Observability Ops Templates (v1.2)

- Prometheus alerts: `ops/prometheus/alerts.yml`
- Grafana dashboard template: `ops/grafana/dashboard-auditai.json`
- Prometheus scrape target endpoint: `/metrics/prometheus`

## Next Part: Production Hardening

### CI and Quality Gates

- Run unit and API tests in CI on every pull request.
- Enforce linting and formatting checks before merge.
- Fail builds when coverage drops below agreed thresholds.

### Runtime Reliability

- Add request timeouts and circuit-breaker behavior for external LLM calls.
- Introduce background job processing for long-running report generation.
- Add dataset pagination limits to protect memory and response times.

### Observability and Ops

- Export metrics to Prometheus text exposition (`/metrics/prometheus`). (Implemented)
- Add dashboard panels for endpoint latency, error rates, and LLM failures (`ops/grafana/dashboard-auditai.json`). (Implemented)
- Add alert rule templates for elevated 5xx rates and LLM failure bursts (`ops/prometheus/alerts.yml`). (Implemented)

### Security and Governance

- Rotate API keys via secret manager integration.
- Add role-based access control for report and anomaly endpoints.
- Add immutable audit logs for explanation and report generation events.

### Delivery Roadmap

- v1.1: CI pipeline + test/coverage gates + lint checks. (Implemented)
- v1.2: External metrics export + alerting + dashboard templates. (Implemented)
- v1.3: Async report jobs + pagination + stronger auth model.
