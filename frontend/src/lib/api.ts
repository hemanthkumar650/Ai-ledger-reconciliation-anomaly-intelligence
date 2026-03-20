import axios, { AxiosInstance } from "axios";
import * as Types from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

class AuditAIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 15000,
      headers: {
        "Content-Type": "application/json",
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      },
    });
  }

  // Health & Status
  async health(): Promise<Types.HealthResponse> {
    const { data } = await this.client.get("/health");
    return data;
  }

  async ready(): Promise<string> {
    const { data } = await this.client.get("/ready");
    return data;
  }

  // Anomalies
  async getAnomalies(offset: number = 0, limit: number = 100): Promise<Types.AnomalyListResponse> {
    const { data } = await this.client.get(`/anomalies?offset=${offset}&limit=${limit}`);
    return data;
  }

  async getAnomaly(transactionId: string): Promise<Types.AnomalyResponse> {
    const { data } = await this.client.get(`/anomaly/${transactionId}`);
    return data;
  }

  async explain(request: Types.ExplainRequest): Promise<Types.ExplainResponse> {
    const { data } = await this.client.post("/explain", request);
    return data;
  }

  // Audit Reports
  async createReportJob(maxTransactions: number = 50): Promise<Types.AuditReportJobResponse> {
    const { data } = await this.client.post("/audit-report/jobs", {
      max_transactions: maxTransactions,
    });
    return data;
  }

  async getReportJobStatus(jobId: string): Promise<Types.AuditReportJobStatusResponse> {
    const { data } = await this.client.get(`/audit-report/jobs/${jobId}`);
    return data;
  }

  // Chat
  async chat(question: string, maxTransactions: number = 30): Promise<Types.ChatResponse> {
    const { data } = await this.client.post("/chat", {
      question,
      max_transactions: maxTransactions,
    });
    return data;
  }

  // Reconciliation
  async getReconciliationSummary(accountFilter?: string): Promise<Types.ReconciliationSummary> {
    const params = new URLSearchParams();
    if (accountFilter) params.append("account_filter", accountFilter);
    const { data } = await this.client.get(`/reconciliation/summary?${params.toString()}`);
    return data;
  }

  async getAccountBalances(accountFilter?: string): Promise<Types.AccountBalance[]> {
    const params = new URLSearchParams();
    if (accountFilter) params.append("account_filter", accountFilter);
    const { data } = await this.client.get(`/reconciliation/balances?${params.toString()}`);
    return data;
  }

  // Metrics (Prometheus)
  async getMetrics(): Promise<string> {
    const { data } = await this.client.get("/metrics/prometheus", {
      headers: { Accept: "text/plain" },
    });
    return data;
  }
}

export const apiClient = new AuditAIClient();
