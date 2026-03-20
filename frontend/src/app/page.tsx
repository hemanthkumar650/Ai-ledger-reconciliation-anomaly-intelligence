"use client";

import { Layout } from "@/components/Layout";
import { DashboardContent } from "@/components/DashboardContent";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function DashboardPage() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <Layout>
        <DashboardContent />
      </Layout>
    </QueryClientProvider>
  );
}
