"use client";

import React from "react";

interface Step {
  stepNumber: string;
  title: string;
  badge: string;
  description: string;
  codeSnippet: string;
  nodeTag: string;
}

const STEPS: Step[] = [
  {
    stepNumber: "01",
    title: "Historical Lineage Ingestion",
    badge: "DataHub Graph Primitive",
    description:
      "Varve traverses DataHub's historical graph layer by layer — not just current dependencies, but when each feature, threshold, or pipeline step changed.",
    codeSnippet: "SELECT event_id, actor, node_urn, timestamp FROM datahub_lineage_events",
    nodeTag: "datahub.lineage.read",
  },
  {
    stepNumber: "02",
    title: "Cross-Model & Actor Correlation",
    badge: "Lineage Archaeology",
    description:
      "Correlates events across un-related models. A threshold shift on Model A made by an engineer who touched Model B before departing is caught automatically.",
    codeSnippet: "JOIN lineage_events ON actor_id AND departure_date_window",
    nodeTag: "archeology.correlation.engine",
  },
  {
    stepNumber: "03",
    title: "Deterministic Precedent Join",
    badge: "Deterministic SQL Logic",
    description:
      "Joins lineage changes directly against your organization's real incident history. The reasoning is deterministic SQL; the LLM only formats the sentence.",
    codeSnippet: "incidents.root_cause_event_id -> lineage_events.event_id",
    nodeTag: "precedent.sql.join",
  },
  {
    stepNumber: "04",
    title: "Idempotent DataHub Write-Back",
    badge: "Hash-Chained Ledger",
    description:
      "Every decision lands back onto DataHub's lineage node as idempotent metadata and gets permanently committed to an append-only verification ledger.",
    codeSnippet: "datahub.emit_metadata(urn, aspect='varveRiskPattern')",
    nodeTag: "datahub.aspect.emit",
  },
];

export default function LineageArchaeology() {
  return (
    <section id="features" className="relative w-full max-w-7xl mx-auto px-6 py-20 border-t border-zinc-900">
      {/* Section Header */}
      <div className="flex flex-col items-center text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider text-[#9B7FF6] uppercase border border-[#9B7FF6]/25 bg-gradient-to-b from-[#9B7FF6]/15 via-zinc-900/60 to-zinc-950/80 backdrop-blur-md">
          <span>How Varve Works</span>
        </div>
        <h2 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl tracking-tight">
          Lineage Archaeology Pipeline
        </h2>
        <p className="text-zinc-400 max-w-2xl text-sm sm:text-base leading-relaxed">
          Composing DataHub primitives — Lineage, Ownership, and Governance tags — to prove where your next production outage will originate.
        </p>
      </div>

      {/* 4-Step Enlarged Cards Grid without Animations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {STEPS.map((step) => (
          <div
            key={step.stepNumber}
            className="relative flex flex-col justify-between p-8 sm:p-9 rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/80 via-zinc-900/40 to-zinc-950/90 backdrop-blur-xl shadow-xl min-h-[320px]"
          >
            <div className="space-y-5">
              {/* Step Number, Badge & Node Tag */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-3xl font-extrabold text-[#9B7FF6]">
                    {step.stepNumber}
                  </span>
                  <span className="px-2.5 py-1 rounded text-[10px] font-semibold tracking-wider uppercase bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                    {step.badge}
                  </span>
                </div>

                <div className="font-mono text-[10px] text-zinc-500">
                  {step.nodeTag}
                </div>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-white leading-snug">
                {step.title}
              </h3>

              <p className="text-sm text-zinc-400 leading-relaxed">
                {step.description}
              </p>
            </div>

            {/* Code Snippet Box */}
            <div className="mt-8 pt-5 border-t border-zinc-800/80">
              <div className="p-4 rounded-xl border border-zinc-800/80 bg-black/60 font-mono text-xs text-indigo-300 leading-relaxed overflow-x-auto truncate">
                {step.codeSnippet}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
