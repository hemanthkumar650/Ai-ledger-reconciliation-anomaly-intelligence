"use client";

import { Layout } from "@/components/Layout";
import { useCreateReportJob, useReportJobStatus } from "@/hooks/useApi";
import { formatDate } from "@/lib/utils";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Unable to generate report right now.";
}

function ReportsContent() {
  const [maxTransactions, setMaxTransactions] = useState(50);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [lastRequestedCount, setLastRequestedCount] = useState(50);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  const createReportJob = useCreateReportJob();
  const { data: jobStatus, isLoading: isPolling } = useReportJobStatus(activeJobId);

  const handleGenerateReport = async () => {
    const normalizedValue = Math.min(500, Math.max(1, Math.trunc(maxTransactions || 1)));
    setMaxTransactions(normalizedValue);
    setSubmitMessage(null);

    try {
      const job = await createReportJob.mutateAsync(normalizedValue);
      setActiveJobId(job.job_id);
      setLastRequestedCount(normalizedValue);
      setSubmitMessage("Report job started. We will keep checking until it finishes.");
    } catch (error) {
      setSubmitMessage(getErrorMessage(error));
    }
  };

  const report = jobStatus?.result;
  const isGenerating =
    createReportJob.isPending || jobStatus?.status === "pending" || jobStatus?.status === "running";

  return (
    <Layout>
      <div className="space-y-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Audit Reports</h1>
            <p className="mt-2 max-w-2xl text-gray-600">
              Generate an AI summary of flagged transactions and track the async report job from one place.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm lg:min-w-[360px]">
            <label htmlFor="max-transactions" className="block text-sm font-medium text-gray-700">
              Transactions to include
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                id="max-transactions"
                type="number"
                min={1}
                max={500}
                value={maxTransactions}
                onChange={(event) => setMaxTransactions(Number(event.target.value))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
              <button
                onClick={handleGenerateReport}
                disabled={createReportJob.isPending}
                className="rounded-lg bg-gray-900 px-4 py-2 font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {createReportJob.isPending ? "Starting..." : "Generate Report"}
              </button>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              The backend samples up to this many flagged transactions when preparing the summary.
            </p>
          </div>
        </div>

        {submitMessage && (
          <div
            className={`rounded-lg border p-4 text-sm ${
              activeJobId
                ? "border-blue-200 bg-blue-50 text-blue-800"
                : "border-red-200 bg-red-50 text-red-700"
            }`}
          >
            {submitMessage}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Latest Job</p>
            <p className="mt-2 break-all text-lg font-semibold text-gray-900">
              {activeJobId || "No report requested yet"}
            </p>
            {activeJobId && (
              <p className="mt-2 text-sm text-gray-600">
                Requested using up to {lastRequestedCount} flagged transactions.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Status</p>
            <p className="mt-2 text-lg font-semibold text-gray-900 capitalize">
              {jobStatus?.status || (createReportJob.isPending ? "pending" : "idle")}
            </p>
            <p className="mt-2 text-sm text-gray-600">
              {isGenerating
                ? "The report is being prepared in the background."
                : activeJobId
                  ? "The latest report job has finished polling."
                  : "Start a report job to see progress here."}
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-medium text-gray-500">Updated</p>
            <p className="mt-2 text-lg font-semibold text-gray-900">
              {jobStatus?.updated_at ? formatDate(jobStatus.updated_at) : "Not available"}
            </p>
            <p className="mt-2 text-sm text-gray-600">
              {isPolling ? "Refreshing job status..." : "Polling pauses automatically when the job ends."}
            </p>
          </div>
        </div>

        {jobStatus?.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {jobStatus.error}
          </div>
        )}

        {report ? (
          <>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Generated Summary</h2>
                  <p className="mt-1 text-sm text-gray-600">
                    Completed {jobStatus?.updated_at ? formatDate(jobStatus.updated_at) : "just now"}
                  </p>
                </div>
                <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
                  Ready
                </span>
              </div>
              <p className="mt-4 whitespace-pre-line text-gray-700">{report.summary}</p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-gray-500">Total Flagged</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{report.total_flagged}</p>
              </div>
              <div className="rounded-lg border border-red-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-red-600">High Risk</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{report.high_risk}</p>
              </div>
              <div className="rounded-lg border border-orange-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-orange-600">Medium Risk</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{report.medium_risk}</p>
              </div>
              <div className="rounded-lg border border-green-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-medium text-green-600">Low Risk</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{report.low_risk}</p>
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-10 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">No report generated yet</h2>
            <p className="mx-auto mt-2 max-w-xl text-gray-600">
              Start a job above to generate a concise audit summary from the latest flagged anomalies.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}

export default function ReportsPage() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ReportsContent />
    </QueryClientProvider>
  );
}
