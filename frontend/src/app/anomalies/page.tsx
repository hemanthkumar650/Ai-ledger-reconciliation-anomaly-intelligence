"use client";

import { useAnomalies } from "@/hooks/useApi";
import { DataTable } from "@/components/DataTable";
import { RiskBadge } from "@/components/RiskBadge";
import { formatCurrency } from "@/lib/utils";
import { useState } from "react";
import Link from "next/link";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { AnomalyResponse } from "@/lib/types";

function AnomaliesContent() {
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const { data, isLoading } = useAnomalies(offset, limit);

  const columns = [
    {
      key: "transaction_id" as const,
      label: "Transaction ID",
      render: (value: unknown, row: AnomalyResponse) => (
        <Link href={`/anomalies/${row.transaction_id}`} className="text-blue-600 hover:underline">
          {String(value)}
        </Link>
      ),
      width: "150px",
    },
    {
      key: "account" as const,
      label: "Account",
      width: "120px",
    },
    {
      key: "amount" as const,
      label: "Amount",
      render: (value: unknown) => formatCurrency(Number(value)),
      align: "right" as const,
      width: "120px",
    },
    {
      key: "anomaly_score" as const,
      label: "Anomaly Score",
      render: (value: unknown) => {
        const score = Number(value);
        const percent = (score * 100).toFixed(0);
        return (
          <div className="flex items-center gap-2">
            <div className="w-20 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  score > 0.85 ? "bg-red-600" : score > 0.6 ? "bg-orange-600" : "bg-green-600"
                }`}
                style={{ width: `${score * 100}%` }}
              />
            </div>
            <span className="text-xs font-medium">{percent}%</span>
          </div>
        );
      },
      width: "180px",
    },
    {
      key: "risk_level" as const,
      label: "Risk Level",
      render: (value: unknown) => <RiskBadge level={String(value)} size="sm" />,
      align: "center" as const,
      width: "100px",
    },
  ];

  const totalPages = data ? Math.ceil(data.total / limit) : 0;
  const currentPage = offset / limit + 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Flagged Anomalies</h1>
        <p className="text-gray-600 mt-2">Total: {data?.total || 0} transactions</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 border border-gray-200">
        <div className="text-sm text-gray-600">Filters available: Search, Risk Level, Amount Range (coming soon)</div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <DataTable
          columns={columns}
          data={data?.items || []}
          isLoading={isLoading}
        />
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Page {currentPage} of {totalPages} ({data.total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="px-4 py-2 border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              ← Previous
            </button>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={currentPage >= totalPages}
              className="px-4 py-2 border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnomaliesPage() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <Link href="/" className="text-blue-600 hover:underline">
              ← Back to Dashboard
            </Link>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-8">
          <AnomaliesContent />
        </main>
      </div>
    </QueryClientProvider>
  );
}
