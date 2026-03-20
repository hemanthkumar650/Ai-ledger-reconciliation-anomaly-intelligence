import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AuditAI - Ledger Anomaly Detection",
  description: "AI-powered audit dashboard for detecting and explaining transaction anomalies",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
