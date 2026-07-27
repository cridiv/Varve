"use client";

import React, { useState } from "react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import TriageDashboard from "@/components/triage/TriageDashboard";
import { useAuth } from "@/lib/useAuth";

export default function TriagePage() {
  const { user, isLoading } = useAuth(true); // redirects to /connect if not logged in

  const [refreshFn, setRefreshFn] = useState<(() => Promise<void>) | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const handleRefreshTrigger = (fn: () => Promise<void>, loading: boolean) => {
    setRefreshFn(() => fn);
    setIsRefreshing(loading);
  };

  const handleManualRefresh = () => {
    if (refreshFn) {
      refreshFn();
    }
  };

  // Show a full-screen loading state while auth is being checked
  // (prevents any flash of protected content before redirect fires)
  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <span className="w-6 h-6 rounded-full border-2 border-[#9B7FF6] border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <DashboardShell
      activeBreadcrumb="/ triage"
      onRefresh={handleManualRefresh}
      isRefreshing={isRefreshing}
    >
      <TriageDashboard onRefreshTrigger={handleRefreshTrigger} />
    </DashboardShell>
  );
}
