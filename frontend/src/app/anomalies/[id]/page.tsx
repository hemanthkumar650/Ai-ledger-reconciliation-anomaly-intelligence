"use client";

import { useAnomaly, useExplain } from "@/hooks/useApi";
import { RiskBadge } from "@/components/RiskBadge";
import { formatCurrency } from "@/lib/utils";
import { useState, useEffect } from "react";
import Link from "next/link";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

interface AnomalyDetailProps {
  params: Promise<{ id: string }>;
}

function AnomalyDetailContent({ transactionId }: { transactionId: string }) {
  const { data: anomaly, isLoading } = useAnomaly(transactionId);
  const { mutate: explain, data: explanation, isPending: isExplaining } = useExplain();

  useEffect(() => {
    if (anomaly && !explanation) {
      explain({ transaction_id: transactionId });
    }
  }, [anomaly, transactionId, explanation, explain]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/2 animate-pulse" />
        <div className="h-96 bg-gray-200 rounded animate-pulse" />
      </div>
    );
  }

  if (!anomaly) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Transaction not found</p>
        <Link href="/anomalies" className="text-blue-600 hover:underline mt-4 inline-block">
          Back to Anomalies
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Transaction {transactionId}</h1>
          <p className="text-gray-600 mt-2">Detailed analysis and AI explanation</p>
        </div>
        <RiskBadge level={anomaly.risk_level} size="lg" />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <p className="text-sm text-gray-600 font-medium">Amount</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">{formatCurrency(anomaly.amount)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <p className="text-sm text-gray-600 font-medium">Account</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">{anomaly.account}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <p className="text-sm text-gray-600 font-medium">Anomaly Score</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">{(anomaly.anomaly_score * 100).toFixed(1)}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
            <div
              className={`h-2 rounded-full ${
                anomaly.anomaly_score > 0.85
                  ? "bg-red-600"
                  : anomaly.anomaly_score > 0.6
                    ? "bg-orange-600"
                    : "bg-green-600"
              }`}
              style={{ width: `${anomaly.anomaly_score * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* AI Explanation */}
      {explanation && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">AI-Generated Explanation</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">Summary</h3>
              <p className="text-gray-700">{explanation.explanation}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold text-gray-900 text-sm mb-1">Possible Cause</h3>
                <p className="text-gray-700 text-sm">{explanation.possible_cause}</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 text-sm mb-1">Recommended Action</h3>
                <p className="text-gray-700 text-sm">{explanation.recommended_action}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {isExplaining && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-700 text-sm">
          Generating AI explanation...
        </div>
      )}

      {/* Metadata */}
      {Object.keys(anomaly.metadata).length > 0 && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Additional Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(anomaly.metadata).map(([key, value]) => (
              <div key={key} className="border-b border-gray-200 pb-3 last:border-0">
                <p className="text-xs text-gray-600 font-medium uppercase tracking-wide">{key}</p>
                <p className="text-gray-900 mt-1">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Link
          href="/anomalies"
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition font-semibold"
        >
          ← Back to List
        </Link>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold">
          Flag for Review
        </button>
      </div>
    </div>
  );
}

export default async function AnomalyDetailPage({ params }: AnomalyDetailProps) {
  const { id } = await params;
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <Link href="/anomalies" className="text-blue-600 hover:underline">
              ← Back to Anomalies
            </Link>
          </div>
        </nav>
        <main className="max-w-4xl mx-auto px-4 py-8">
          <AnomalyDetailContent transactionId={id} />
        </main>
      </div>
    </QueryClientProvider>
  );
}
