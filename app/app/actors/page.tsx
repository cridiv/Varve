"use client";

import React from "react";
import DashboardShell from "@/components/dashboard/DashboardShell";
import Link from "next/link";

export default function ActorHistoryPage() {
  const sampleActors = [
    {
      actor: "J. Alvarez",
      status: "DEPARTED (<90d)",
      incidentCount: 2,
      crossModelImpact: "High (3 downstream models)",
      lastEvent: "2026-05-20: Modified threshold on customers dataset",
    },
    {
      actor: "R. Chen",
      status: "ACTIVE",
      incidentCount: 0,
      crossModelImpact: "Low (1 model)",
      lastEvent: "2026-06-01: Added column on products dataset",
    },
    {
      actor: "M. Santos",
      status: "ACTIVE",
      incidentCount: 0,
      crossModelImpact: "None",
      lastEvent: "2026-07-01: Modified threshold on countries dataset",
    },
  ];

  return (
    <DashboardShell activeBreadcrumb="/ actor">
      <div className="max-w-5xl space-y-6">
        <div className="flex flex-col space-y-1 pb-4 border-b border-white/10">
          <h1 className="text-xl font-mono font-extrabold text-white">
            Actor History Inspector
          </h1>
          <p className="text-xs text-zinc-400">
            Cross-model incident correlation tracked per engineer/actor profile.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {sampleActors.map((a, idx) => (
            <div
              key={idx}
              className="p-5 rounded-xl border border-white/10 bg-[#12141a]/90 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-bold text-white">
                    {a.actor}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                      a.status.includes("DEPARTED")
                        ? "bg-rose-950/80 text-rose-400 border border-rose-800"
                        : "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                    }`}
                  >
                    {a.status}
                  </span>
                </div>

                <div className="text-xs font-mono text-zinc-400">
                  Confirmed Incidents: <strong className="text-white">{a.incidentCount}</strong>
                </div>
              </div>

              <div className="text-xs text-zinc-400 space-y-1">
                <div>Cross-Model Lineage Impact: <span className="text-zinc-200">{a.crossModelImpact}</span></div>
                <div>Latest Lineage Event: <span className="font-mono text-indigo-300">{a.lastEvent}</span></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
