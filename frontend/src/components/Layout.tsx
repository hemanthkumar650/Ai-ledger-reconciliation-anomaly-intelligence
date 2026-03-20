"use client";

import { PropsWithChildren } from "react";
import { Header } from "./Header";

export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
