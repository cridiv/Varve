"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardShell from "@/components/dashboard/DashboardShell";
import ActorHistoryBoard from "@/components/triage/ActorHistoryBoard";
import { fetchRiskRankings } from "@/lib/api";

function ActorHistoryContent() {
  const searchParams = useSearchParams();
  const actorParam = searchParams.get("actor");

  const [actors, setActors] = useState<string[]>([]);
  const [selectedActor, setSelectedActor] = useState<string>("");

  useEffect(() => {
    async function loadActorsFromLineage() {
      try {
        const findings = await fetchRiskRankings();
        const extracted = new Set<string>();

        // Always include core DataHub owners & lineage actors
        extracted.add("Ian Chen");
        extracted.add("jonny1");
        extracted.add("J. Alvarez");
        extracted.add("K. Vance");

        findings.forEach((f) => {
          if (f.actor) {
            const clean = f.actor.replace(/\s*\(Departed.*?\)/i, "").trim();
            if (clean) extracted.add(clean);
          }
          if (f.routed_to_team) {
            const cleanTeam = f.routed_to_team.split("(")[0].trim();
            if (cleanTeam) extracted.add(cleanTeam);
          }
        });

        if (actorParam) {
          const cleanParam = actorParam.replace(/\s*\(Departed.*?\)/i, "").trim();
          if (cleanParam) extracted.add(cleanParam);
        }

        const actorList = Array.from(extracted);
        setActors(actorList);

        if (actorList.length > 0) {
          const initial = actorParam
            ? actorParam.replace(/\s*\(Departed.*?\)/i, "").trim()
            : actorList[0];
          setSelectedActor(initial);
        } else if (actorParam) {
          const cleanParam = actorParam.replace(/\s*\(Departed.*?\)/i, "").trim();
          setSelectedActor(cleanParam);
        }
      } catch (err) {
        console.warn("Failed extracting actors from lineage findings:", err);
      }
    }

    loadActorsFromLineage();
  }, [actorParam]);

  return (
    <div className="space-y-6">
      {/* Dynamic Actor Selector Bar — Extracted Directly from Lineage & DataHub Ownership */}
      {actors.length > 0 && (
        <div className="flex items-center gap-2 pb-2 border-b border-zinc-800/80 flex-wrap">
          <span className="text-xs font-mono text-zinc-500 uppercase mr-2">
            Select Actor / Owner Profile:
          </span>
          {actors.map((actor) => (
            <button
              key={actor}
              onClick={() => setSelectedActor(actor)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                selectedActor === actor
                  ? "bg-[#9B7FF6]/20 text-[#9B7FF6] border border-[#9B7FF6]/40 shadow-[0_0_12px_rgba(155,127,246,0.2)]"
                  : "bg-black text-zinc-400 hover:text-zinc-200 border border-zinc-800"
              }`}
            >
              {actor}
            </button>
          ))}
        </div>
      )}

      {/* Main Screen 3 Board */}
      {selectedActor ? (
        <ActorHistoryBoard actorName={selectedActor} />
      ) : (
        <div className="p-8 text-center text-xs font-mono text-zinc-500">
          No actor lineage history found.
        </div>
      )}
    </div>
  );
}

export default function ActorHistoryPage() {
  return (
    <DashboardShell activeBreadcrumb="/ actor">
      <Suspense fallback={<div className="p-8 text-center text-xs font-mono text-zinc-500">Loading actor lineage history...</div>}>
        <ActorHistoryContent />
      </Suspense>
    </DashboardShell>
  );
}
