# AuditAI - Part 1 (Backend Foundation)

This first increment includes:
- FastAPI backend scaffold
- Secure `.env` based configuration
- CSV anomaly loading service
- Azure OpenAI (and optional Ollama) explanation service
- Routes:
  - `GET /health`
  - `GET /anomalies`
  - `GET /anomaly/{transaction_id}`
  - `POST /explain`

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
  "transaction_id": "TXN-1001"
}
```

## Azure deployment notes (preview)
- Backend can be deployed to Azure App Service using startup command:
  - `gunicorn -k uvicorn.workers.UvicornWorker backend.main:app`
- Keep secrets in App Service Configuration (Application settings), not in repo.

## Next Part
Part 2 will add:
- `/audit-report` and `/chat`
- frontend (React + Vite)
- risk distribution endpoint for dashboard chart
- deployment files for Azure Static Web Apps
