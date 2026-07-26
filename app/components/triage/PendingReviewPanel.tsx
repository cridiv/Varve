"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  fetchCandidateIncidents,
  confirmCandidateIncident,
  dismissCandidateIncident,
} from "@/lib/api";

export interface CandidateIncident {
  candidate_id: string;
  model_id: string;
  anomaly_metric: string;
  anomaly_value: number;
  anomaly_date: string;
  candidate_event_id: string;
  days_between: number;
  proposed_description: string;
  status: string;
  created_at: string;
}

interface PendingReviewPanelProps {
  onCandidateActionSuccess?: () => void;
}

export default function PendingReviewPanel({ onCandidateActionSuccess }: PendingReviewPanelProps) {
  const [candidates, setCandidates] = useState<CandidateIncident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [animatingOutIds, setAnimatingOutIds] = useState<Set<string>>(new Set());

  const fetchCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchCandidateIncidents();
      setCandidates(data);
    } catch (err) {
      console.warn("Failed fetching candidates:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  const handleAction = async (candidate_id: string, action: "confirm" | "dismiss") => {
    setProcessingId(candidate_id);
    try {
      if (action === "confirm") {
        await confirmCandidateIncident(candidate_id);
      } else {
        await dismissCandidateIncident(candidate_id);
      }
    } catch (err) {
      console.warn(`Error handling candidate ${action}:`, err);
    } finally {
      setAnimatingOutIds((prev) => new Set(prev).add(candidate_id));

      setTimeout(() => {
        setCandidates((prev) => prev.filter((c) => c.candidate_id !== candidate_id));
        setAnimatingOutIds((prev) => {
          const next = new Set(prev);
          next.delete(candidate_id);
          return next;
        });
        setProcessingId(null);

        if (onCandidateActionSuccess) {
          onCandidateActionSuccess();
        }
      }, 400);
    }
  };

  const getModelDisplayName = (model_id: string) => {
    const parts = model_id.split(".");
    return parts[parts.length - 1]?.replace(",PROD)", "") || model_id;
  };

  if (loading) {
    return (
      <div className="p-3 bg-black border border-[#1f2028] rounded-xl animate-pulse flex items-center justify-between text-xs text-zinc-500">
        <span>Loading candidate incidents...</span>
      </div>
    );
  }

  // Collapsed quiet state when zero pending candidates per Part B §0.5
  if (candidates.length === 0) {
    return (
      <div className="px-4 py-2 bg-black border border-[#1f2028] rounded-lg flex items-center justify-between text-xs text-zinc-500 font-mono">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600" />
          <span>No candidates awaiting review.</span>
        </div>
        <span className="text-[10px] text-zinc-600">Self-bootstrapping loop active</span>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {/* Header Label */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          <span>Pending Review — Candidate Incidents ({candidates.length})</span>
        </div>
        <span className="text-[11px] font-mono text-zinc-500">
          Human verification loop
        </span>
      </div>

      {/* Candidates List */}
      <div className="space-y-2">
        {candidates.map((cand) => {
          const isAnimating = animatingOutIds.has(cand.candidate_id);
          const isBusy = processingId === cand.candidate_id;

          return (
            <div
              key={cand.candidate_id}
              className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 bg-black border border-amber-900/40 rounded-xl transition-all duration-400 ${
                isAnimating ? "opacity-0 scale-95 -translate-y-2" : "opacity-100 scale-100"
              }`}
            >
              {/* Left Details */}
              <div className="flex items-start gap-3 min-w-0 flex-1">
                {/* Activity Pulse Glyph */}
                <div className="w-2 h-2 rounded-full bg-amber-400 shrink-0 mt-1.5 animate-pulse" />

                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-white">
                      {getModelDisplayName(cand.model_id)}
                    </span>
                    <span className="text-[10px] font-mono text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/60">
                      {cand.anomaly_metric}: {cand.anomaly_value}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">
                      ({cand.days_between}d gap from lineage change)
                    </span>
                  </div>

                  <p className="text-xs text-zinc-400 leading-snug truncate">
                    {cand.proposed_description}
                  </p>
                </div>
              </div>

              {/* Inline Action Buttons */}
              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                <button
                  onClick={() => handleAction(cand.candidate_id, "confirm")}
                  disabled={isBusy}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-700/60 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                  title="Confirm as organizational incident"
                >
                  {isBusy ? "Processing..." : "Confirm"}
                </button>

                <button
                  onClick={() => handleAction(cand.candidate_id, "dismiss")}
                  disabled={isBusy}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 transition-colors cursor-pointer disabled:opacity-50"
                  title="Dismiss candidate"
                >
                  Dismiss
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
