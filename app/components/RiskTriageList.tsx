"use client";

import React, { useState } from "react";

interface Finding {
  id: string;
  modelName: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  evidenceTier: "ORG-VALIDATED" | "UNVALIDATED" | "INDUSTRY-GENERAL";
  summary: string;
  details: string;
  precedent: string;
  precedentCount: number;
  avgLagDays: number;
  owner: string;
  hash: string;
  actor: string;
  changeDate: string;
  lineagePath: string;
}

const FINDINGS: Finding[] = [
  {
    id: "f-1",
    modelName: "fraud_model_v4",
    severity: "HIGH",
    evidenceTier: "ORG-VALIDATED",
    summary: "Undocumented threshold change made under traffic pressure",
    details:
      "Threshold lowered during Q3 traffic spike by an engineer who left the team three weeks later. DataHub lineage correlates this actor across 2 past incidents on Payments Platform.",
    precedent: "Preceded 2 of last 3 incidents (Avg detection lag: 11 days)",
    precedentCount: 2,
    avgLagDays: 11,
    owner: "Payments Platform",
    hash: "a4f8e...721b",
    actor: "alex.m@company.com (Departed)",
    changeDate: "4 months ago",
    lineagePath: "feature_store.payment_risk -> fraud_model_v4 -> checkout_api",
  },
  {
    id: "f-2",
    modelName: "churn_model_v3",
    severity: "LOW",
    evidenceTier: "UNVALIDATED",
    summary: "Orphaned experiment artifact with no measurable impact",
    details:
      "Superficially resembles an unreviewed change, but carries zero incident precedent anywhere in organizational history. Automatically downgraded to LOW to prevent alert fatigue.",
    precedent: "0 Incident Precedents (Downgraded to LOW)",
    precedentCount: 0,
    avgLagDays: 0,
    owner: "User Lifecycle",
    hash: "9b3c1...84ef",
    actor: "dev.ci@company.com",
    changeDate: "8 months ago",
    lineagePath: "user_events.retention -> churn_model_v3 -> batch_scorer",
  },
  {
    id: "f-3",
    modelName: "new_signup_model",
    severity: "MEDIUM",
    evidenceTier: "INDUSTRY-GENERAL",
    summary: "Unreviewed feature addition on new model (Cold Start)",
    details:
      "New team with no organizational incident history yet. Evidence fallback uses published post-mortem industry base rates, capping initial guess at MEDIUM.",
    precedent: "Industry-General Fallback (Auto-upgrades on 1st confirmation)",
    precedentCount: 0,
    avgLagDays: 14,
    owner: "Onboarding Team",
    hash: "5e2d9...3a1c",
    actor: "sarah.k@company.com",
    changeDate: "2 weeks ago",
    lineagePath: "onboarding.form_inputs -> new_signup_model -> welcome_flow",
  },
];

export default function RiskTriageList() {
  const [selectedId, setSelectedId] = useState<string>("f-1");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [actionEmitted, setActionEmitted] = useState<boolean>(false);

  const selectedFinding = FINDINGS.find((f) => f.id === selectedId) || FINDINGS[0];

  const handleCopyHash = (hash: string) => {
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleEmitDataHub = () => {
    setActionEmitted(true);
    setTimeout(() => setActionEmitted(false), 2500);
  };

  return (
    <section id="triage" className="relative w-full max-w-7xl mx-auto px-6 py-20">
      {/* Section Header */}
      <div className="flex flex-col items-center text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider text-[#9B7FF6] uppercase border border-[#9B7FF6]/25 bg-gradient-to-b from-[#9B7FF6]/15 via-zinc-900/60 to-zinc-950/80 backdrop-blur-md">
          <span>Live Triage Console</span>
        </div>
        <h2 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl tracking-tight">
          Interactive Risk Archaeology Console
        </h2>
        <p className="text-zinc-400 max-w-2xl text-sm sm:text-base leading-relaxed">
          Select any production model to inspect its DataHub lineage trail, precedent breakdown, and evidence verification tier.
        </p>
      </div>

      {/* Master-Detail Command Center Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Ranked Model List (4 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-semibold tracking-wider text-zinc-500 uppercase px-2 mb-2">
            Ranked Production Models ({FINDINGS.length})
          </div>

          {FINDINGS.map((finding) => {
            const isSelected = finding.id === selectedId;
            const isHigh = finding.severity === "HIGH";
            const isMed = finding.severity === "MEDIUM";

            return (
              <button
                key={finding.id}
                onClick={() => setSelectedId(finding.id)}
                className={`w-full text-left p-5 rounded-2xl border transition-all cursor-pointer select-none flex flex-col justify-between space-y-3 ${
                  isSelected
                    ? "border-[#9B7FF6]/60 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 shadow-[0_0_25px_-5px_rgba(155,127,246,0.3)]"
                    : "border-white/10 bg-zinc-900/40 hover:bg-zinc-900/70 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-bold text-white">
                    `{finding.modelName}`
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${
                      isHigh
                        ? "bg-rose-950/60 border-rose-800/60 text-rose-400"
                        : isMed
                        ? "bg-amber-950/60 border-amber-800/60 text-amber-400"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400"
                    }`}
                  >
                    {finding.severity}
                  </span>
                </div>

                <div className="text-xs text-zinc-400 font-medium line-clamp-1">
                  {finding.summary}
                </div>

                <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1">
                  <span
                    className={`px-2 py-0.5 rounded text-[9px] font-semibold uppercase ${
                      finding.evidenceTier === "ORG-VALIDATED"
                        ? "bg-[#9B7FF6]/20 text-[#9B7FF6]"
                        : finding.evidenceTier === "INDUSTRY-GENERAL"
                        ? "bg-cyan-950/60 text-cyan-400"
                        : "bg-zinc-800 text-zinc-400"
                    }`}
                  >
                    {finding.evidenceTier.replace("_", " ")}
                  </span>
                  <span>{finding.owner}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Right Column: Deep Lineage & Evidence Inspector (7 cols) */}
        <div className="lg:col-span-7 p-7 rounded-2xl border border-white/15 bg-gradient-to-b from-zinc-900/90 via-zinc-900/60 to-zinc-950/95 backdrop-blur-2xl shadow-2xl space-y-6">
          {/* Inspector Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
            <div>
              <div className="text-xs text-zinc-500 font-mono">INSPECTOR TARGET</div>
              <h3 className="font-mono text-xl font-bold text-white">
                `{selectedFinding.modelName}`
              </h3>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-lg text-xs font-bold uppercase border ${
                  selectedFinding.severity === "HIGH"
                    ? "bg-rose-950/80 border-rose-800 text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.3)]"
                    : selectedFinding.severity === "MEDIUM"
                    ? "bg-amber-950/80 border-amber-800 text-amber-400"
                    : "bg-zinc-900 border-zinc-800 text-zinc-400"
                }`}
              >
                {selectedFinding.severity} RISK
              </span>
              <span
                className={`px-3 py-1 rounded-lg text-xs font-semibold uppercase ${
                  selectedFinding.evidenceTier === "ORG-VALIDATED"
                    ? "bg-[#9B7FF6]/25 text-[#9B7FF6] border border-[#9B7FF6]/40"
                    : selectedFinding.evidenceTier === "INDUSTRY-GENERAL"
                    ? "bg-cyan-950/80 text-cyan-400 border border-cyan-800"
                    : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                }`}
              >
                {selectedFinding.evidenceTier.replace("_", " ")}
              </span>
            </div>
          </div>

          {/* Finding Details */}
          <div className="space-y-4">
            <div>
              <div className="text-xs text-zinc-500 font-semibold mb-1">FINDING SUMMARY</div>
              <p className="text-sm font-semibold text-zinc-100">{selectedFinding.summary}</p>
              <p className="text-xs text-zinc-400 leading-relaxed mt-1">{selectedFinding.details}</p>
            </div>

            {/* Archaeology Lineage Graph Trail */}
            <div className="p-4 rounded-xl bg-black/60 border border-zinc-800/80 space-y-2">
              <div className="text-[11px] font-semibold text-[#9B7FF6] uppercase tracking-wider">
                DataHub Lineage Archaeology Trail
              </div>
              <div className="font-mono text-xs text-indigo-300 overflow-x-auto py-1">
                {selectedFinding.lineagePath}
              </div>
            </div>

            {/* Metrics Breakdown Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-2">
              <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                <div className="text-[10px] text-zinc-500 uppercase">Incident Precedents</div>
                <div className="text-lg font-bold text-white mt-0.5">{selectedFinding.precedentCount} Events</div>
              </div>

              <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                <div className="text-[10px] text-zinc-500 uppercase">Actor Lineage</div>
                <div className="text-xs font-semibold text-zinc-200 truncate mt-1">{selectedFinding.actor}</div>
              </div>

              <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 col-span-2 sm:col-span-1">
                <div className="text-[10px] text-zinc-500 uppercase">Audit Hash</div>
                <button
                  onClick={() => handleCopyHash(selectedFinding.hash)}
                  className="text-xs font-mono text-[#9B7FF6] hover:underline cursor-pointer mt-1 block truncate"
                >
                  {copiedHash === selectedFinding.hash ? "Copied!" : selectedFinding.hash}
                </button>
              </div>
            </div>
          </div>

          {/* Action Footer Button */}
          <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between">
            <div className="text-xs text-zinc-500">
              Target Owner: <strong className="text-zinc-300">{selectedFinding.owner}</strong>
            </div>

            <button
              onClick={handleEmitDataHub}
              disabled={actionEmitted}
              className="relative group inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs text-white transition-all cursor-pointer border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 shadow-md hover:border-white/25 active:translate-y-[1px]"
            >
              {actionEmitted ? (
                <span className="text-emerald-400 font-bold">✓ DataHub Aspect Emitted</span>
              ) : (
                <>
                  <span>Emit to DataHub</span>
                  <span className="text-[#9B7FF6]">&rarr;</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
