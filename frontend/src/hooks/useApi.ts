import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type {
  AuditReportJobResponse,
  ChatResponse,
  ExplainRequest,
  ExplainResponse,
} from "@/lib/types";

export const useAnomalies = (offset: number = 0, limit: number = 100) => {
  return useQuery({
    queryKey: ["anomalies", offset, limit],
    queryFn: () => apiClient.getAnomalies(offset, limit),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useAnomaly = (transactionId: string | null) => {
  return useQuery({
    queryKey: ["anomaly", transactionId],
    queryFn: () => (transactionId ? apiClient.getAnomaly(transactionId) : null),
    enabled: Boolean(transactionId),
  });
};

export const useExplain = () => {
  return useMutation<ExplainResponse, Error, ExplainRequest>({
    mutationFn: (request: ExplainRequest) => apiClient.explain(request),
  });
};

export const useCreateReportJob = () => {
  return useMutation<AuditReportJobResponse, Error, number | undefined>({
    mutationFn: (maxTransactions?: number) => apiClient.createReportJob(maxTransactions),
  });
};

export const useReportJobStatus = (jobId: string | null) => {
  return useQuery({
    queryKey: ["reportJob", jobId],
    queryFn: () => (jobId ? apiClient.getReportJobStatus(jobId) : null),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2000;
    },
  });
};

export const useChat = () => {
  return useMutation<ChatResponse, Error, { question: string; maxTransactions?: number }>({
    mutationFn: ({ question, maxTransactions }: { question: string; maxTransactions?: number }) =>
      apiClient.chat(question, maxTransactions),
  });
};

export const useReconciliationSummary = (accountFilter?: string) => {
  return useQuery({
    queryKey: ["reconciliation-summary", accountFilter],
    queryFn: () => apiClient.getReconciliationSummary(accountFilter),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useAccountBalances = (accountFilter?: string) => {
  return useQuery({
    queryKey: ["account-balances", accountFilter],
    queryFn: () => apiClient.getAccountBalances(accountFilter),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
