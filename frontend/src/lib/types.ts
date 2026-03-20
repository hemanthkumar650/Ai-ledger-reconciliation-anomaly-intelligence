/**
 * Type definitions for AuditAI API responses
 */

export type RiskLevel = "High" | "Medium" | "Low" | "Unknown";

export interface AnomalyResponse {
  transaction_id: string;
  amount: number;
  account: string;
  anomaly_score: number; // 0.0-1.0
  risk_level: RiskLevel;
  metadata: Record<string, unknown>;
}

export interface AnomalyListResponse {
  total: number;
  offset: number;
  limit: number;
  items: AnomalyResponse[];
}

export interface ExplainRequest {
  transaction_id?: string;
  transaction?: AnomalyResponse;
}

export interface ExplainResponse {
  transaction_id: string;
  explanation: string;
  risk_level: string;
  possible_cause: string;
  recommended_action: string;
}

export interface AuditReportJobResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
}

export interface AuditReportResponse {
  summary: string;
  total_flagged: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
}

export interface AuditReportJobStatusResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  result?: AuditReportResponse;
  error?: string;
}

export interface ChatRequest {
  question: string;
  max_transactions?: number;
}

export interface ChatResponse {
  answer: string;
}

export interface ReconciliationIssue {
  issue_type: string;
  severity: "High" | "Medium" | "Low";
  account?: string;
  description: string;
  amount?: number;
  transaction_ids: string[];
}

export interface ReconciliationSummary {
  total_accounts: number;
  balanced_accounts: number;
  unbalanced_accounts: number;
  total_variance: number;
  issues: ReconciliationIssue[];
  completion_percentage: number;
  last_reconciled: string;
}

export interface AccountBalance {
  account: string;
  local_balance: number;
  doc_balance: number;
  transaction_count: number;
  currency: string;
  variance: number;
}

export interface HealthResponse {
  status: "ok" | "error";
  version?: string;
}
