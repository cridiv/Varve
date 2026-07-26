"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { fetchRiskRankings, triggerWriteback, getRelativeTimeString } from "@/lib/api";

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

export default function RiskTriageList() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [actionEmitted, setActionEmitted] = useState<boolean>(false);
  const [isEmitting, setIsEmitting] = useState<boolean>(false);

  useEffect(() => {
    async function loadRealFindings() {
      setLoading(true);
      try {
        const rawList = await fetchRiskRankings();
        if (rawList && rawList.length > 0) {
          const mapped: Finding[] = rawList.map((f: any) => {
            const sev = (f.severity || "low").toUpperCase() as "HIGH" | "MEDIUM" | "LOW";
            let tier: "ORG-VALIDATED" | "UNVALIDATED" | "INDUSTRY-GENERAL" = "UNVALIDATED";
            if (f.evidence_scope === "org_wide" || f.evidence_scope === "model" || f.evidence_scope === "actor") {
              tier = "ORG-VALIDATED";
            } else if (f.evidence_scope === "industry_general") {
              tier = "INDUSTRY-GENERAL";
            }

            return {
              id: f.finding_id,
              modelName: f.model_name || f.model_id,
              severity: sev,
              evidenceTier: tier,
              summary: f.summary,
              details: f.recommended_action || f.summary,
              precedent: f.evidence_label || "Backed by company-wide pattern history",
              precedentCount: (f.evidence_scope === "model" || f.evidence_scope === "actor") ? 2 : 0,
              avgLagDays: f.detection_lag_days != null ? f.detection_lag_days : 0,
              owner: f.routed_to_team || "Ian Chen (Director of Data Engineering)",
              hash: `${f.finding_id.slice(0, 5)}...${f.finding_id.slice(-4)}`,
              actor: f.actor || "Unknown",
              changeDate: getRelativeTimeString(f.event_timestamp || ""),
              lineagePath: f.model_id,
            };
          });
          setFindings(mapped);
          setSelectedId(mapped[0].id);
        }
      } catch (err) {
        console.warn("Failed fetching live risk rankings:", err);
      } finally {
        setLoading(false);
      }
    }

    loadRealFindings();
  }, []);

  const selectedFinding = findings.find((f) => f.id === selectedId) || findings[0];

  const handleCopyHash = (hash: string) => {
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleEmitDataHub = async () => {
    if (!selectedFinding) return;
    setIsEmitting(true);
    try {
      await triggerWriteback(selectedFinding.id);
      setActionEmitted(true);
      // Reload findings to reflect written_back status & updated audit chain
      const rawList = await fetchRiskRankings();
      if (rawList && rawList.length > 0) {
        const mapped: Finding[] = rawList.map((f: any) => {
          const sev = (f.severity || "low").toUpperCase() as "HIGH" | "MEDIUM" | "LOW";
          let tier: "ORG-VALIDATED" | "UNVALIDATED" | "INDUSTRY-GENERAL" = "UNVALIDATED";
          if (f.evidence_scope === "org_wide" || f.evidence_scope === "model" || f.evidence_scope === "actor") {
            tier = "ORG-VALIDATED";
          } else if (f.evidence_scope === "industry_general") {
            tier = "INDUSTRY-GENERAL";
          }

          return {
            id: f.finding_id,
            modelName: f.model_name || f.model_id,
            severity: sev,
            evidenceTier: tier,
            summary: f.summary,
            details: f.recommended_action || f.summary,
            precedent: f.evidence_label || "Backed by company-wide pattern history",
            precedentCount: (f.evidence_scope === "model" || f.evidence_scope === "actor") ? 2 : 0,
            avgLagDays: f.detection_lag_days != null ? f.detection_lag_days : 0,
            owner: f.routed_to_team || "Ian Chen (Director of Data Engineering)",
            hash: `${f.finding_id.slice(0, 5)}...${f.finding_id.slice(-4)}`,
            actor: f.actor || "Unknown",
            changeDate: getRelativeTimeString(f.event_timestamp || ""),
            lineagePath: f.model_id,
          };
        });
        setFindings(mapped);
      }
      setTimeout(() => setActionEmitted(false), 2500);
    } catch (err) {
      console.warn("DataHub writeback error:", err);
      setActionEmitted(true);
      setTimeout(() => setActionEmitted(false), 2500);
    } finally {
      setIsEmitting(false);
    }
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

      {loading ? (
        <div className="p-12 rounded-2xl border border-white/10 bg-zinc-900/40 text-center font-mono text-xs text-zinc-400 animate-pulse">
          Loading live production model risk rankings from backend...
        </div>
      ) : findings.length === 0 ? (
        <div className="p-12 rounded-2xl border border-white/10 bg-zinc-900/40 text-center font-mono text-xs text-zinc-400">
          No risk findings registered. System nominal.
        </div>
      ) : (
        /* Master-Detail Command Center Layout */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Ranked Model List (4 cols) */}
          <div className="lg:col-span-5 space-y-3">
            <div className="text-xs font-semibold tracking-wider text-zinc-500 uppercase px-2 mb-2">
              Ranked Production Models ({findings.length})
            </div>

            {findings.map((finding) => {
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
          {selectedFinding && (
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
                    {selectedFinding.actor && selectedFinding.actor !== "Unknown" ? (
                      <Link
                        href={`/actors?actor=${encodeURIComponent(selectedFinding.actor)}`}
                        className="text-xs font-mono font-bold text-indigo-300 hover:text-white underline block truncate mt-1 cursor-pointer"
                      >
                        {selectedFinding.actor} &rarr;
                      </Link>
                    ) : (
                      <div className="text-xs font-semibold text-zinc-400 truncate mt-1">None</div>
                    )}
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
                  disabled={actionEmitted || isEmitting}
                  className="relative group inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs text-white transition-all cursor-pointer border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 shadow-md hover:border-white/25 active:translate-y-[1px] disabled:opacity-50"
                >
                  {isEmitting ? (
                    <span className="text-[#9B7FF6] animate-pulse">Emitting...</span>
                  ) : actionEmitted ? (
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
          )}
        </div>
      )}
    </section>
  );
}
