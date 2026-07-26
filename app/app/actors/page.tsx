"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardShell from "@/components/dashboard/DashboardShell";
import ActorHistoryBoard from "@/components/triage/ActorHistoryBoard";

function ActorHistoryContent() {
  const searchParams = useSearchParams();
  const actorParam = searchParams.get("actor");

  const [selectedActor, setSelectedActor] = useState<string>("J. Alvarez");

  useEffect(() => {
    if (actorParam) {
      setSelectedActor(actorParam);
    }
  }, [actorParam]);

  const actors = ["J. Alvarez", "R. Chen"];

  return (
    <div className="space-y-6">
      {/* Quick Actor Selector Bar */}
      <div className="flex items-center gap-2 pb-2 border-b border-zinc-800/80">
        <span className="text-xs font-mono text-zinc-500 uppercase mr-2">
          Select Actor Profile:
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

      {/* Main Screen 3 Board */}
      <ActorHistoryBoard actorName={selectedActor} />
    </div>
  );
}

export default function ActorHistoryPage() {
  return (
    <DashboardShell activeBreadcrumb="/ actor">
      <Suspense fallback={<div className="p-8 text-center text-xs font-mono text-zinc-500">Loading actor history...</div>}>
        <ActorHistoryContent />
      </Suspense>
    </DashboardShell>
  );
}
