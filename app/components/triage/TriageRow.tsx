"use client";

import React from "react";
import { GroupedModelFinding, EvidenceScope, Severity } from "./types";

interface TriageRowProps {
  item: GroupedModelFinding;
}

export default function TriageRow({ item }: TriageRowProps) {
  const { primaryFinding, additionalCount } = item;
  const { finding_id, model_name, summary, severity, evidence_scope, routed_to_team } = primaryFinding;

  // Exact wording per Part B §5: "Org-validated", "Actor-validated", "Industry baseline"
  const getEvidenceTierLabel = (scope: EvidenceScope): string => {
    switch (scope) {
      case "org_wide":
      case "model":
        return "Org-validated";
      case "actor":
        return "Actor-validated";
      case "industry_general":
        return "Industry baseline";
      default:
        return "Org-validated";
    }
  };

  // Swatch styling for 2-dimensional evidence visual band (Part B §5)
  const getEvidenceBandStyle = (severity: Severity, scope: EvidenceScope) => {
    let hueClasses = "";
    if (severity === "high") {
      hueClasses = "bg-rose-500 border-rose-400";
    } else if (severity === "medium") {
      hueClasses = "bg-amber-500 border-amber-400";
    } else {
      hueClasses = "bg-emerald-500 border-emerald-400";
    }

    let tierClasses = "";
    if (scope === "org_wide" || scope === "model") {
      tierClasses = "opacity-100 border-solid border";
    } else if (scope === "actor") {
      tierClasses = "opacity-[0.75] border-solid border";
    } else {
      tierClasses = "opacity-[0.40] border-dashed border-2";
    }

    return `${hueClasses} ${tierClasses}`;
  };

  return (
    <a
      href={`/findings/${finding_id}`}
      className="group relative flex items-center justify-between gap-4 px-4.5 py-3.5 rounded-xl border border-[#1f2028] bg-black hover:bg-[#121318] hover:border-zinc-700 transition-colors select-none cursor-pointer"
    >
      {/* Left Group: Swatch + Model Name + Summary Clause */}
      <div className="flex items-center gap-4 min-w-0 flex-1">
        {/* 2D Evidence Band Swatch (~8px x 32px) */}
        <div
          aria-label={`Evidence Band (${severity} risk, ${getEvidenceTierLabel(evidence_scope)})`}
          className={`w-2 h-8 rounded-[2px] shrink-0 transition-transform group-hover:scale-105 ${getEvidenceBandStyle(
            severity,
            evidence_scope
          )}`}
          title={`Severity: ${severity.toUpperCase()} | Tier: ${getEvidenceTierLabel(evidence_scope)}`}
        />

        {/* Model Name & Truncated Summary Clause */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-4 min-w-0 flex-1">
          <span className="font-mono text-sm font-bold text-white group-hover:text-[#9B7FF6] transition-colors truncate shrink-0 max-w-[220px] sm:max-w-[280px]">
            {model_name}
          </span>

          <span className="text-xs text-zinc-400 truncate font-normal min-w-0">
            {summary}
          </span>
        </div>
      </div>

      {/* Right Group: Evidence Tier Label, Owner, +N Indicator */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {/* Evidence Tier Label Badge */}
        <span
          className={`px-2.5 py-1 rounded-md text-[10px] font-semibold tracking-wide uppercase select-none ${
            evidence_scope === "org_wide" || evidence_scope === "model"
              ? "bg-[#9B7FF6]/15 text-[#9B7FF6] border border-[#9B7FF6]/30 shadow-[inset_0_1px_0_0_rgba(155,127,246,0.2)]"
              : evidence_scope === "actor"
              ? "bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)]"
              : "bg-zinc-900 text-zinc-400 border border-dashed border-zinc-700"
          }`}
        >
          {getEvidenceTierLabel(evidence_scope)}
        </span>

        {/* Routed Owner (Omit completely if null/empty per spec) */}
        {routed_to_team && routed_to_team.trim().length > 0 && (
          <span className="hidden lg:inline-block text-xs font-medium text-zinc-400 group-hover:text-zinc-300 transition-colors">
            {routed_to_team}
          </span>
        )}

        {/* +N More Secondary Indicator Tag */}
        {additionalCount > 0 && (
          <span
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-800/90 text-zinc-300 border border-zinc-700 hover:bg-zinc-700 cursor-default shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1)]"
            title={`${additionalCount} additional finding(s) for ${model_name}`}
          >
            +{additionalCount} more
          </span>
        )}

        {/* Chevron Arrow */}
        <span className="text-zinc-600 group-hover:text-zinc-300 transition-colors text-xs font-semibold">
          &rarr;
        </span>
      </div>
    </a>
  );
}
