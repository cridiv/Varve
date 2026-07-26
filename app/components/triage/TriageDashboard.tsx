"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Finding, GroupedModelFinding, Severity, EvidenceScope } from "./types";
import { fetchRiskRankings } from "@/lib/api";
import SummaryStatRow from "./SummaryStatRow";
import PendingReviewPanel from "./PendingReviewPanel";
import TriageRow from "./TriageRow";
import TriageSkeleton from "./TriageSkeleton";

interface TriageDashboardProps {
  onRefreshTrigger?: (refreshFn: () => Promise<void>, isLoading: boolean) => void;
}

export default function TriageDashboard({ onRefreshTrigger }: TriageDashboardProps) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Fetch from GET /models/risk-ranking via unified API client (Part B §1)
  const loadRankings = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchRiskRankings();
      setFindings(data);
    } catch (err) {
      console.warn("Error fetching risk rankings:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRankings();
  }, [loadRankings]);

  // Expose refresh function to shell
  useEffect(() => {
    if (onRefreshTrigger) {
      onRefreshTrigger(loadRankings, isLoading);
    }
  }, [onRefreshTrigger, loadRankings, isLoading]);

  // Priority score helper for sorting evidence tiers within same severity (Part B §3)
  const getScopePriority = (scope: EvidenceScope): number => {
    switch (scope) {
      case "org_wide":
      case "model":
        return 1;
      case "actor":
        return 2;
      case "industry_general":
        return 3;
      default:
        return 1;
    }
  };

  // Severity rank helper: high (1) > medium (2) > low (3)
  const getSeverityRank = (sev: Severity): number => {
    switch (sev.toLowerCase() as Severity) {
      case "high":
        return 1;
      case "medium":
        return 2;
      case "low":
        return 3;
      default:
        return 2;
    }
  };

  // De-duplication & Grouping Logic per Part B §2 & §3
  const processedSections = useMemo(() => {
    if (findings.length === 0) return { high: [], medium: [], low: [], totalCount: 0 };

    // 1. Group by model_id
    const modelGroups = new Map<string, Finding[]>();
    findings.forEach((f) => {
      const existing = modelGroups.get(f.model_id) || [];
      existing.push(f);
      modelGroups.set(f.model_id, existing);
    });

    // 2. De-duplicate each model: pick single highest severity finding as primary
    const groupedList: GroupedModelFinding[] = [];

    modelGroups.forEach((modelFindings, model_id) => {
      const sortedModelFindings = [...modelFindings].sort((a, b) => {
        const sevDiff = getSeverityRank(a.severity) - getSeverityRank(b.severity);
        if (sevDiff !== 0) return sevDiff;

        const scopeDiff = getScopePriority(a.evidence_scope) - getScopePriority(b.evidence_scope);
        if (scopeDiff !== 0) return scopeDiff;

        const dateA = new Date(a.created_at || a.event_timestamp || 0).getTime();
        const dateB = new Date(b.created_at || b.event_timestamp || 0).getTime();
        return dateB - dateA;
      });

      const primaryFinding = sortedModelFindings[0];
      const additionalCount = sortedModelFindings.length - 1;

      groupedList.push({
        model_id,
        primaryFinding,
        additionalCount,
      });
    });

    // 3. Categorize into High, Medium, Low sections
    const high: GroupedModelFinding[] = [];
    const medium: GroupedModelFinding[] = [];
    const low: GroupedModelFinding[] = [];

    groupedList.forEach((item) => {
      const sev = item.primaryFinding.severity.toLowerCase() as Severity;
      if (sev === "high") high.push(item);
      else if (sev === "medium") medium.push(item);
      else low.push(item);
    });

    // 4. Sort each section strictly per Part B §3
    const sortSection = (items: GroupedModelFinding[]) => {
      return items.sort((a, b) => {
        const fA = a.primaryFinding;
        const fB = b.primaryFinding;

        const scopeDiff = getScopePriority(fA.evidence_scope) - getScopePriority(fB.evidence_scope);
        if (scopeDiff !== 0) return scopeDiff;

        const dateA = new Date(fA.created_at || fA.event_timestamp || 0).getTime();
        const dateB = new Date(fB.created_at || fB.event_timestamp || 0).getTime();
        return dateB - dateA;
      });
    };

    return {
      high: sortSection(high),
      medium: sortSection(medium),
      low: sortSection(low),
      totalCount: groupedList.length,
    };
  }, [findings]);

  return (
    <div className="w-full space-y-6">
      {/* 0.3 — Summary Stat Row (High, Medium, Low, % Org-validated) */}
      <SummaryStatRow findings={findings} />

      {/* 0.5 — Pending Review Panel (Candidate Incident Loop) */}
      <PendingReviewPanel onCandidateActionSuccess={loadRankings} />

      {/* Main Content Area */}
      {isLoading ? (
        <TriageSkeleton />
      ) : processedSections.totalCount === 0 ? (
        /* Empty State per Part B §7 */
        <div className="flex flex-col items-center justify-center py-20 px-6 text-center rounded-xl border border-[#1f2028] bg-black space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center text-emerald-400 text-base font-bold">
            ✓
          </div>
          <p className="text-sm font-medium text-zinc-300">
            No active findings — Varve is watching, nothing to triage right now.
          </p>
        </div>
      ) : (
        /* 3 Visual Severity Sections per Part B §4 */
        <div className="space-y-8">
          {/* 1. HIGH RISK SECTION */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1 pb-2 border-b border-rose-900/30">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <h2 className="text-xs font-bold tracking-wider uppercase text-zinc-200">
                  High Risk ({processedSections.high.length})
                </h2>
              </div>
              <span className="text-[11px] font-mono text-zinc-500">
                Action Required
              </span>
            </div>

            {processedSections.high.length === 0 ? (
              <div className="p-3.5 rounded-xl border border-[#1f2028] bg-black text-xs text-zinc-500 font-mono italic">
                High Risk (0)
              </div>
            ) : (
              <div className="space-y-2.5">
                {processedSections.high.map((item) => (
                  <TriageRow key={item.model_id} item={item} />
                ))}
              </div>
            )}
          </section>

          {/* 2. MEDIUM RISK SECTION */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1 pb-2 border-b border-amber-900/30">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <h2 className="text-xs font-bold tracking-wider uppercase text-zinc-200">
                  Medium Risk ({processedSections.medium.length})
                </h2>
              </div>
              <span className="text-[11px] font-mono text-zinc-500">
                Watchlist
              </span>
            </div>

            {processedSections.medium.length === 0 ? (
              <div className="p-3.5 rounded-xl border border-[#1f2028] bg-black text-xs text-zinc-500 font-mono italic">
                Medium Risk (0)
              </div>
            ) : (
              <div className="space-y-2.5">
                {processedSections.medium.map((item) => (
                  <TriageRow key={item.model_id} item={item} />
                ))}
              </div>
            )}
          </section>

          {/* 3. LOW RISK SECTION */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1 pb-2 border-b border-zinc-800/60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <h2 className="text-xs font-bold tracking-wider uppercase text-zinc-200">
                  Low Risk ({processedSections.low.length})
                </h2>
              </div>
              <span className="text-[11px] font-mono text-zinc-500">
                Downgraded / Routine
              </span>
            </div>

            {processedSections.low.length === 0 ? (
              <div className="p-3.5 rounded-xl border border-[#1f2028] bg-black text-xs text-zinc-500 font-mono italic">
                Low Risk (0)
              </div>
            ) : (
              <div className="space-y-2.5">
                {processedSections.low.map((item) => (
                  <TriageRow key={item.model_id} item={item} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
