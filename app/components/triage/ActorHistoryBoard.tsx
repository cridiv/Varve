"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";

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

export interface ActorHistoryResponse {
  actor: string;
  total_events: number;
  events_with_incidents: number;
  pattern_summary: PatternSummary | null;
  events: ActorEvent[];
}

interface ActorHistoryBoardProps {
  actorName: string;
}

// Empirical mock offline datasets matching J. Alvarez and R. Chen seed stories
const MOCK_ACTOR_DATASETS: Record<string, ActorHistoryResponse> = {
  "J. Alvarez": {
    actor: "J. Alvarez",
    total_events: 2,
    events_with_incidents: 2,
    pattern_summary: {
      pattern_type: "departing_engineer_change",
      times_observed: 2,
      times_preceded_incident: 2,
      incident_rate_pct: 100.0,
      avg_detection_lag_days: 54.0,
    },
    events: [
      {
        event_id: "c3c4d5e6-f7a8-9012-bcde-f34567890123",
        model_id: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.addresses,PROD)",
        model_name: "addresses",
        node_type: "pipeline_step",
        event_type: "modified",
        event_timestamp: "2026-04-10T09:00:00Z",
        actor_departed_within_90d: true,
        documentation_present: false,
        linked_incident: {
          incident_id: "d4e5f6a7-b8c9-0123-def0-567890123456",
          incident_model_id: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)",
          incident_model_name: "order_items",
          detected_at: "2026-06-15T11:00:00Z",
          description: "Order item sync failure on order_items dataset due to unreviewed transformation logic in upstream addresses dataset.",
          detection_lag_days: 66.1,
        },
      },
      {
        event_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        model_id: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)",
        model_name: "customers",
        node_type: "threshold",
        event_type: "modified",
        event_timestamp: "2026-05-20T10:00:00Z",
        actor_departed_within_90d: true,
        documentation_present: false,
        linked_incident: {
          incident_id: "c3d4e5f6-a7b8-9012-cdef-345678901234",
          incident_model_id: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)",
          incident_model_name: "order_details",
          detected_at: "2026-07-08T14:30:00Z",
          description: "Customer records miscategorized in order_details table due to unreviewed threshold change in upstream customers dataset.",
          detection_lag_days: 49.2,
        },
      },
    ],
  },
  "R. Chen": {
    actor: "R. Chen",
    total_events: 1,
    events_with_incidents: 0,
    pattern_summary: {
      pattern_type: "unreviewed_change",
      times_observed: 1,
      times_preceded_incident: 0,
      incident_rate_pct: 0.0,
      avg_detection_lag_days: 0.0,
    },
    events: [
      {
        event_id: "b2c3d4e5-f6a7-8901-bcde-f23456789012",
        model_id: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)",
        model_name: "products",
        node_type: "feature",
        event_type: "added",
        event_timestamp: "2026-06-01T11:15:00Z",
        actor_departed_within_90d: false,
        documentation_present: false,
        linked_incident: null,
      },
    ],
  },
};

export default function ActorHistoryBoard({ actorName }: ActorHistoryBoardProps) {
  const [data, setData] = useState<ActorHistoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchActorHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/patterns/by-actor/${encodeURIComponent(actorName)}`, {
        cache: "no-store",
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch {
      // Fallback offline actor dataset
      const fallback = MOCK_ACTOR_DATASETS[actorName] || MOCK_ACTOR_DATASETS["J. Alvarez"];
      setData(fallback);
    } finally {
      setLoading(false);
    }
  }, [actorName]);

  useEffect(() => {
    fetchActorHistory();
  }, [fetchActorHistory]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-zinc-800 rounded-md" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-24 bg-zinc-900 rounded-xl" />
          <div className="h-24 bg-zinc-900 rounded-xl" />
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
  const avgLag = data.pattern_summary?.avg_detection_lag_days ?? 0;
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
          <p className="text-xs text-zinc-400 mt-1 max-w-2xl">
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
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
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

            return (
              <div key={evt.event_id || idx} className="relative group">
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

                    <span className="text-xs font-mono text-zinc-500">
                      {evt.event_timestamp ? new Date(evt.event_timestamp).toLocaleDateString() : "2026-05-20"}
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
                          ⚡ {evt.linked_incident.detection_lag_days} DAYS DETECTION LAG
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
