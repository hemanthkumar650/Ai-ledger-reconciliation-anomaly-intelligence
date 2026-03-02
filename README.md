# AuditAI

## 1) What and Why
AuditAI is a FastAPI backend that detects anomalous ledger transactions and explains audit risk with LLM-generated reasoning so auditors can move from raw flags to actionable decisions faster.

## 2) Architecture Diagram (Mermaid.js)
```mermaid
flowchart LR
    U[Auditor / Client] --> API[FastAPI API Layer]
    API --> A[Anomaly Service]
    A --> D[(CSV Ledger Dataset)]
    API --> L[LLM Service]
    L --> AZ[Azure OpenAI]
    L --> OL[Ollama Fallback]
    API --> M[Observability Middleware]
    M --> MET[/metrics + /metrics/prometheus]
    API --> J[Async Report Job Service]
```

## 3) Results / Benchmarks (Real Numbers)
- Measurement date: March 2, 2026
- Dataset size: `533,009` total ledger rows
- Flagged anomalies after filtering `label != regular`: `100` rows (`0.02%`)
- Risk distribution on flagged set: `70 High`, `30 Medium`, `0 Low`, `0 Unknown`
- `AnomalyService.list_anomalies()` over 20 runs:
  - Average: `1328.40 ms`
  - P50: `1298.91 ms`
  - P95: `1626.07 ms`
- `AnomalyService.get_by_transaction_id()` over 20 runs:
  - Average: `1140.80 ms`
  - P50: `1122.56 ms`
  - P95: `1367.70 ms`

## 4) Technical Decisions
- Chose FastAPI for typed request/response contracts, async support, and clean route-service separation.
- Kept the anomaly layer CSV-backed for deterministic local development and reproducible test behavior.
- Added dual LLM providers (Azure primary, Ollama fallback) to reduce deployment coupling.
- Added observability middleware plus Prometheus exposition for production monitoring and alerting.
- Implemented role-based API keys and async report jobs to support safer multi-user usage and non-blocking report generation.
