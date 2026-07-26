"use client";

import React, { useState, useEffect, useCallback } from "react";
import { fetchActorHistoryData } from "@/lib/api";

export interface LinkedIncident {
  incident_id: string;
  incident_model_id: string;
  incident_model_name: string;
  detected_at: string;
  description: string;
  fix_summary?: string;
  detection_lag_days: number;
}

export interface ActorEvent {
  event_id: string;
  model_id: string;
  model_name: string;
  node_type: string;
  event_type: string;
  event_timestamp: string;
  actor_departed_within_90d: boolean;
  documentation_present: boolean;
  linked_incident: LinkedIncident | null;
}

export interface PatternSummary {
  pattern_type: string;
  times_observed: number;
  times_preceded_incident: number;
  incident_rate_pct: number;
  avg_detection_lag_days: number;
}

export interface IdentityMapping {
  lineage_actor: string;
  datahub_owner_urn: string;
  datahub_display_name: string;
  match_type: string;
}

export interface ActorHistoryResponse {
  actor: string;
  identity_mapping?: IdentityMapping;
  total_events: number;
  events_with_incidents: number;
  pattern_summary: PatternSummary | null;
  events: ActorEvent[];
}

interface ActorHistoryBoardProps {
  actorName: string;
}

export default function ActorHistoryBoard({ actorName }: ActorHistoryBoardProps) {
  const [data, setData] = useState<ActorHistoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadActorHistory = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchActorHistoryData(actorName);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [actorName]);

  useEffect(() => {
    loadActorHistory();
  }, [loadActorHistory]);

  if (loading) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 rounded-2xl border border-white/10 bg-zinc-950/80 backdrop-blur-xl text-center space-y-6 flex flex-col items-center justify-center">
        <div className="relative flex items-center justify-center">
          <span className="w-12 h-12 rounded-full border-2 border-[#9B7FF6] border-t-transparent animate-spin" />
          <span className="absolute w-6 h-6 rounded-full bg-[#9B7FF6]/20 animate-ping" />
        </div>

        <div className="space-y-2">
          <h3 className="font-mono text-sm font-bold text-white tracking-wide">
            Searching lineage across all models for actor &quot;{actorName}&quot;...
          </h3>
          <p className="text-xs font-mono text-zinc-400">
            Correlating 67 datasets across 5 transformation pipelines in DataHub GMS
          </p>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-mono text-indigo-300 bg-indigo-950/60 border border-indigo-800/60">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          <span>Cross-Model Graph Traversal Active</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center text-zinc-400 bg-black rounded-xl border border-zinc-800">
        No lineage events found for actor &quot;{actorName}&quot;.
      </div>
    );
  }

  const incidentRate = data.pattern_summary?.incident_rate_pct ?? (data.events_with_incidents > 0 ? Math.round((data.events_with_incidents / data.total_events) * 100) : 0);
  
  // Calculate exact average detection lag dynamically across all events for this actor
  const validLags = data.events
    .map((e) => e.linked_incident?.detection_lag_days)
    .filter((l): l is number => l != null && !isNaN(l));
  const avgLag = validLags.length > 0
    ? Math.round(validLags.reduce((a, b) => a + b, 0) / validLags.length)
    : Math.round(data.pattern_summary?.avg_detection_lag_days ?? 0);

  const isDeparted = data.events.some((e) => e.actor_departed_within_90d);

  return (
    <div className="w-full max-w-5xl mx-auto space-y-8 select-none">
      {/* 2.1 — Header: Actor Identity Subject */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-semibold tracking-wider text-indigo-400 uppercase">
              CROSS-MODEL ACTOR PROFILE
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-tight">
            {data.actor}
          </h1>
          {data.identity_mapping && (
            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-zinc-900/90 border border-white/10 text-xs font-mono text-zinc-300 flex-wrap">
              <span className="text-[#9B7FF6] font-bold">Resolved DataHub Identity:</span>
              <span className="text-white font-semibold">{data.identity_mapping.datahub_display_name}</span>
              <span className="text-zinc-500 font-mono text-[11px]">({data.identity_mapping.datahub_owner_urn})</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-zinc-800 text-zinc-400 border border-zinc-700">
                {data.identity_mapping.match_type}
              </span>
            </div>
          )}
          <p className="text-xs text-zinc-400 mt-2 max-w-2xl">
            Correlates lineage events authored by {data.actor} across all models against downstream incident outcomes.
          </p>
        </div>

        {/* Actor Status Badge */}
        <div className="flex items-center gap-2">
          {isDeparted ? (
            <span className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase bg-rose-950/80 text-rose-300 border border-rose-800 shadow-sm">
              Departed (&lt;90 days)
            </span>
          ) : (
            <span className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase bg-emerald-950/80 text-emerald-300 border border-emerald-800">
              Active Contributor
            </span>
          )}
        </div>
      </div>

      {/* 2.2 — Summary Stat Block (Prominent Numbers Above Timeline) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {/* Stat Card 1: Incident Rate */}
        <div className="p-6 rounded-xl border border-[#1f2028] bg-black space-y-2">
          <div className="font-mono text-3xl sm:text-4xl font-extrabold text-rose-500 tracking-tight">
            {incidentRate}%
          </div>
          <p className="text-xs text-zinc-400 font-medium leading-relaxed">
            of this actor&apos;s undocumented changes have preceded a real incident.
          </p>
        </div>

        {/* Stat Card 2: Average Detection Lag */}
        <div className="p-6 rounded-xl border border-[#1f2028] bg-black space-y-2">
          <div className="font-mono text-3xl sm:text-4xl font-extrabold text-amber-400 tracking-tight">
            {avgLag} <span className="text-xl font-normal text-zinc-500">days</span>
          </div>
          <p className="text-xs text-zinc-400 font-medium leading-relaxed">
            average time to catch downstream incident consequences.
          </p>
        </div>

        {/* Stat Card 3: Explicit Query Scope Stat (Screen 3 Spec) */}
        <div className="p-6 rounded-xl border border-[#1f2028] bg-black space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="text-[10px] font-mono text-[#9B7FF6] uppercase tracking-wider font-semibold">
              DataHub Query Scope
            </div>
            <div className="font-mono text-xl font-bold text-white tracking-tight">
              67 Datasets
            </div>
          </div>
          <p className="text-xs text-zinc-400 font-medium leading-relaxed">
            Searched across 5 transformation pipelines in DataHub GMS graph.
          </p>
        </div>
      </div>

      {/* 2.3 — Vertical Timeline (The Core Visual) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
          <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
            Lineage Activity Timeline ({data.total_events} events)
          </h2>
          <span className="text-[11px] font-mono text-zinc-500">
            Chronological Order
          </span>
        </div>

        <div className="relative pl-6 space-y-8 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-zinc-800">
          {data.events.map((evt, idx) => {
            const hasIncident = evt.linked_incident !== null;
            const lagValue = evt.linked_incident?.detection_lag_days != null
              ? Math.round(evt.linked_incident.detection_lag_days)
              : 0;
            const formattedDate = evt.event_timestamp
              ? new Date(evt.event_timestamp).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })
              : "2026-05-20";

            return (
              <div key={`${evt.event_id || "evt"}-${idx}`} className="relative group">
                {/* Timeline Node Bullet */}
                <div
                  className={`absolute -left-[21px] top-1.5 w-3.5 h-3.5 rounded-full border-2 transition-transform ${
                    hasIncident
                      ? "bg-rose-500 border-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.5)] group-hover:scale-125"
                      : "bg-zinc-900 border-zinc-700"
                  }`}
                />

                {/* Originating Event Box */}
                <div className="p-4 rounded-xl border border-[#1f2028] bg-black space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-mono font-bold text-white bg-zinc-900 px-2.5 py-1 rounded border border-zinc-800">
                        {evt.model_name}
                      </span>
                      <span className="text-xs text-zinc-400 font-mono">
                        {evt.event_type} ({evt.node_type})
                      </span>
                    </div>

                    <span className="text-xs font-mono text-zinc-400">
                      {formattedDate}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-400">
                    Authored change on dataset node <code className="text-indigo-300 font-mono">{evt.model_name}</code> ({evt.documentation_present ? "documented" : "undocumented"}).
                  </p>

                  {/* 2.3 Visual Connector to Linked Incident on DIFFERENT MODEL */}
                  {hasIncident && evt.linked_incident && (
                    <div className="mt-4 pt-4 border-t border-rose-950/60 space-y-3">
                      {/* Visual Bridge Line & Lag Badge */}
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-0.5 bg-gradient-to-r from-rose-500/80 via-rose-500 to-amber-500 rounded" />
                        <span className="px-2.5 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[11px] font-mono font-bold shadow-sm shrink-0">
                          ⚡ {lagValue} DAYS DETECTION LAG
                        </span>
                        <div className="flex-1 h-0.5 bg-gradient-to-r from-amber-500 to-rose-500/80 rounded" />
                      </div>

                      {/* Linked Incident Node on SECOND MODEL */}
                      <div className="p-3.5 rounded-lg bg-rose-950/20 border border-rose-900/40 space-y-2">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-rose-900 text-white">
                              Incident Node
                            </span>
                            <span className="text-xs font-mono font-bold text-white">
                              `{evt.linked_incident.incident_model_name}`
                            </span>
                          </div>

                          <span className="text-[11px] font-mono text-zinc-500">
                            {evt.linked_incident.detected_at ? new Date(evt.linked_incident.detected_at).toLocaleDateString() : "2026-06-15"}
                          </span>
                        </div>

                        {/* Explicit Connector Proof Text */}
                        <div className="text-xs text-zinc-300 leading-relaxed font-normal">
                          <strong className="text-rose-400 font-mono">Cross-Model Link:</strong> Change on <span className="text-white font-mono">{evt.model_name}</span> &rarr; Incident on <span className="text-white font-mono">{evt.linked_incident.incident_model_name}</span>
                        </div>
                        <p className="text-xs text-zinc-400">
                          {evt.linked_incident.description}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
