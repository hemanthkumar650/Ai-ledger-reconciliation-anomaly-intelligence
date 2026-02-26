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

## Next Part: Production Readiness

### Testing Strategy

- Implemented `tests/test_anomaly_service.py` for anomaly filtering and transaction lookup behavior.
- Implemented `tests/test_api.py` for `/explain` validation, auth guard behavior, and `/metrics` assertions.
- Implemented `tests/test_llm_service.py` to verify sensitive prompt-field redaction.

### Observability

- Added `ObservabilityMiddleware` with request IDs and JSON structured request logs.
- Added in-memory endpoint metrics for request count, error count, and average latency.
- Added LLM provider telemetry counters: total calls, retries, and failures.

### Security and Compliance

- Added optional API-key authentication (`x-api-key`) for non-health routes.
- Added sensitive-field redaction before LLM explain prompts are constructed.
- Request IDs are returned to clients for traceability in logs.

### Roadmap

- Support larger datasets via pagination and async processing.
- Add configurable risk-scoring thresholds by account/category.
- Add report export formats (PDF/CSV) for audit handoff workflows.
