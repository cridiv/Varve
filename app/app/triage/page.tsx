"use client";

import React, { useState } from "react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import TriageDashboard from "@/components/triage/TriageDashboard";

export default function TriagePage() {
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
