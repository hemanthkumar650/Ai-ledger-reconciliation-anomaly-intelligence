"use client";

import { useAnomalies, useReconciliationSummary } from "@/hooks/useApi";
import { KPICard } from "@/components/KPICard";
import { RiskBadge } from "@/components/RiskBadge";
import Link from "next/link";

export function DashboardContent() {
  const { data: anomaliesData } = useAnomalies(0, 500);
  const { data: reconcilData } = useReconciliationSummary();

  const totalFlagged = anomaliesData?.total || 0;
  const highRisk = anomaliesData?.items?.filter((a) => a.risk_level === "High").length || 0;
  const mediumRisk = anomaliesData?.items?.filter((a) => a.risk_level === "Medium").length || 0;
  const lowRisk = anomaliesData?.items?.filter((a) => a.risk_level === "Low").length || 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Audit Dashboard</h1>
        <p className="text-gray-600 mt-2">Monitor transaction anomalies and audit health</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Flagged"
          value={totalFlagged}
          subtitle="All anomalies"
          icon="⚠️"
        />
        <KPICard title="High Risk" value={highRisk} subtitle="Require review" icon="🔴" />
        <KPICard title="Medium Risk" value={mediumRisk} subtitle="Monitor" icon="🟠" />
        <KPICard title="Low Risk" value={lowRisk} subtitle="Standard" icon="🟢" />
      </div>

      {/* Risk Distribution */}
      {anomaliesData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Risk Distribution</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RiskBadge level="High" />
                <span className="text-gray-700">{highRisk} transactions</span>
              </div>
              <div className="w-48 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-red-600 h-2 rounded-full"
                  style={{ width: `${totalFlagged > 0 ? (highRisk / totalFlagged) * 100 : 0}%` }}
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RiskBadge level="Medium" />
                <span className="text-gray-700">{mediumRisk} transactions</span>
              </div>
              <div className="w-48 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-orange-600 h-2 rounded-full"
                  style={{ width: `${totalFlagged > 0 ? (mediumRisk / totalFlagged) * 100 : 0}%` }}
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RiskBadge level="Low" />
                <span className="text-gray-700">{lowRisk} transactions</span>
              </div>
              <div className="w-48 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full"
                  style={{ width: `${totalFlagged > 0 ? (lowRisk / totalFlagged) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reconciliation Summary */}
      {reconcilData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Reconciliation Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-gray-200 rounded p-4">
              <p className="text-sm text-gray-600">Completion</p>
              <p className="text-2xl font-bold text-gray-900">
                {reconcilData.completion_percentage.toFixed(1)}%
              </p>
            </div>
            <div className="border border-gray-200 rounded p-4">
              <p className="text-sm text-gray-600">Unbalanced Accounts</p>
              <p className="text-2xl font-bold text-orange-600">{reconcilData.unbalanced_accounts}</p>
            </div>
            <div className="border border-gray-200 rounded p-4">
              <p className="text-sm text-gray-600">Total Variance</p>
              <p className="text-2xl font-bold text-gray-900">${reconcilData.total_variance.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}

      {/* CTA Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/anomalies"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg p-6 text-center transition font-semibold"
        >
          Review Anomalies →
        </Link>
        <Link
          href="/reports"
          className="bg-gray-900 hover:bg-gray-800 text-white rounded-lg p-6 text-center transition font-semibold"
        >
          Generate Report →
        </Link>
      </div>
    </div>
  );
}
