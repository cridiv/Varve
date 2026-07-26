"use client";

import React from "react";

export default function TriageSkeleton() {
  const sections = [
    { title: "High Risk", count: 2 },
    { title: "Medium Risk", count: 1 },
    { title: "Low Risk", count: 1 },
  ];

  return (
    <div className="space-y-8 animate-pulse">
      {sections.map((section, idx) => (
        <div key={idx} className="space-y-3">
          {/* Section Header Skeleton */}
          <div className="flex items-center justify-between pb-2 border-b border-white/5">
            <div className="h-4 w-28 bg-zinc-800 rounded-md" />
            <div className="h-3 w-20 bg-zinc-800/60 rounded-md" />
          </div>

          {/* Row Skeletons */}
          <div className="space-y-2.5">
            {Array.from({ length: section.count }).map((_, rIdx) => (
              <div
                key={rIdx}
                className="flex items-center justify-between px-4 py-3.5 rounded-xl border border-white/5 bg-[#12141a]/60"
              >
                <div className="flex items-center gap-3.5 flex-1">
                  <div className="w-2 h-8 bg-zinc-800 rounded-sm shrink-0" />
                  <div className="space-y-1.5 flex-1 max-w-lg">
                    <div className="h-4 w-36 bg-zinc-800 rounded-md" />
                    <div className="h-3 w-64 bg-zinc-800/60 rounded-md" />
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <div className="h-6 w-24 bg-zinc-800 rounded-md" />
                  <div className="h-4 w-20 bg-zinc-800/60 rounded-md hidden lg:block" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
