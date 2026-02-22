# AuditAI - Part 2 (Backend LLM APIs)

This increment includes:
- FastAPI backend scaffold
- Secure `.env` based configuration
- CSV anomaly loading service
- Azure OpenAI (and optional Ollama) explanation service
- Routes:
  - `GET /health`
  - `GET /anomalies`
  - `GET /anomaly/{transaction_id}`
  - `POST /explain`
  - `POST /audit-report`
  - `POST /chat`

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.template .env
uvicorn backend.main:app --reload --port 8000
```

## Quick test
- Health: `http://localhost:8000/health`
- Anomalies: `http://localhost:8000/anomalies`
- Explain (example body):

```json
{
  "transaction_id": "331521"
}
```

- Audit report (example body):

```json
{
  "max_transactions": 50
}
```

- Chat (example body):

```json
{
  "question": "What are the top risk patterns in flagged transactions?",
  "max_transactions": 30
}
```

## Azure deployment notes (preview)
- Backend can be deployed to Azure App Service using startup command:
  - `gunicorn -k uvicorn.workers.UvicornWorker backend.main:app`
- Keep secrets in App Service Configuration (Application settings), not in repo.

## Next Part
Part 3 will add:
- frontend dashboard (React + Vite)
- risk distribution endpoint for chart-ready data
- deployment files for Azure Static Web Apps
