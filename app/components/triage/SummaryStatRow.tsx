"use client";

import React from "react";
import { Finding } from "./types";

interface SummaryStatRowProps {
  findings: Finding[];
}

export default function SummaryStatRow({ findings }: SummaryStatRowProps) {
  // Aggregate stats client-side per Part B §0.3
  const highCount = findings.filter(
    (f) => f.severity.toLowerCase() === "high"
  ).length;

  const mediumCount = findings.filter(
    (f) => f.severity.toLowerCase() === "medium"
  ).length;

  const lowCount = findings.filter(
    (f) => f.severity.toLowerCase() === "low"
  ).length;

  const totalFindings = findings.length;

  const orgValidatedCount = findings.filter(
    (f) => f.evidence_scope === "org_wide" || f.evidence_scope === "model"
  ).length;

  const orgValidatedPercentage =
    totalFindings > 0
      ? Math.round((orgValidatedCount / totalFindings) * 100)
      : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 mb-8">
      {/* Card 1: High Risk Count */}
      <div className="rounded-xl p-5 border border-[#1f2028] bg-black flex flex-col justify-between space-y-2">
        <span className="font-mono text-2xl sm:text-3xl font-extrabold text-rose-500 tracking-tight">
          {highCount}
        </span>
        <span className="text-xs font-medium text-zinc-400">High risk</span>
      </div>

      {/* Card 2: Medium Risk Count */}
      <div className="rounded-xl p-5 border border-[#1f2028] bg-black flex flex-col justify-between space-y-2">
        <span className="font-mono text-2xl sm:text-3xl font-extrabold text-amber-500 tracking-tight">
          {mediumCount}
        </span>
        <span className="text-xs font-medium text-zinc-400">Medium risk</span>
      </div>

      {/* Card 3: Low Risk Count */}
      <div className="rounded-xl p-5 border border-[#1f2028] bg-black flex flex-col justify-between space-y-2">
        <span className="font-mono text-2xl sm:text-3xl font-extrabold text-emerald-400 tracking-tight">
          {lowCount}
        </span>
        <span className="text-xs font-medium text-zinc-400">Low risk</span>
      </div>

      {/* Card 4: % Org-Validated */}
      <div className="rounded-xl p-5 border border-[#1f2028] bg-black flex flex-col justify-between space-y-2">
        <span className="font-mono text-2xl sm:text-3xl font-extrabold text-[#9B7FF6] tracking-tight">
          {orgValidatedPercentage}%
        </span>
        <span className="text-xs font-medium text-zinc-400">Org-validated</span>
      </div>
    </div>
  );
}
