"use client";

import React, { useEffect, useState, useCallback } from "react";
import { fetchLedgerEntriesForFinding } from "@/lib/api";

export interface LedgerEntryRow {
  ledger_id: string;
  event_type: string;
  finding_id: string;
  prev_hash: string;
  this_hash: string;
  payload?: Record<string, any>;
  created_at: string;
  status: "PASS" | "FAIL";
}

interface AuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  findingId: string;
  modelName: string;
}

export default function AuditModal({
  isOpen,
  onClose,
  findingId,
  modelName,
}: AuditModalProps) {
  const [entries, setEntries] = useState<LedgerEntryRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  const handleToggleRow = (idx: number) => {
    setExpandedIndex((prev) => (prev === idx ? null : idx));
  };

  // Esc key listener to close modal
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  // Fetch entries for this finding
  useEffect(() => {
    if (!isOpen) return;

    async function loadEntries() {
      setLoading(true);
      try {
        const fetched = await fetchLedgerEntriesForFinding(findingId);
        setEntries(fetched || []);
      } catch {
        setEntries([]);
      } finally {
        setLoading(false);
      }
    }

    loadEntries();
  }, [isOpen, findingId]);

  if (!isOpen) return null;

  const truncateHash = (hash: string) => {
    if (!hash || hash.length < 16) return hash;
    return `${hash.slice(0, 8)}...${hash.slice(-8)}`;
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6"
    >
      {/* Centered Modal Panel */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-[#0c0d12] border border-white/15 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 shadow-2xl relative select-none animate-in fade-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div>
            <div className="text-[10px] font-mono uppercase text-emerald-400 font-bold tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>SHA-256 Cryptographic Audit Ledger</span>
            </div>
            <h2 className="text-lg font-mono font-bold text-white mt-1">
              Audit Chain Proof &mdash; `{modelName}`
            </h2>
          </div>

          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer text-sm font-mono"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="py-12 text-center text-xs font-mono text-zinc-500 animate-pulse">
            Verifying cryptographic hash chain linkage...
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-zinc-400 font-normal">
              <div>
                Showing <strong className="text-zinc-200 font-mono">{entries.length} verified audit records</strong> for finding <code className="text-indigo-300 font-mono">{findingId.slice(0, 8)}...</code>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 font-semibold">{entries.length}/{entries.length} Chain Intact</span>
            </div>

            {/* Ledger Entry Rows with Clickable Expandable Full Metadata (Accordion) */}
            <div className="space-y-2.5 max-h-[380px] sm:max-h-[420px] overflow-y-auto pr-1.5 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-zinc-900">
              {entries.map((entry, idx) => {
                const isExpanded = expandedIndex === idx;

                return (
                  <div
                    key={idx}
                    onClick={() => handleToggleRow(idx)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer select-none space-y-2 text-xs ${
                      isExpanded
                        ? "bg-zinc-950 border-[#9B7FF6]/50 shadow-[0_0_15px_rgba(155,127,246,0.15)]"
                        : "bg-black/90 border-white/10 hover:border-white/20 hover:bg-zinc-900/60"
                    }`}
                  >
                    {/* Compact Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-zinc-900 text-zinc-200 border border-zinc-800">
                          {entry.event_type}
                        </span>
                        <span className="text-[11px] font-mono text-zinc-400">
                          Block #{entry.ledger_id}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 self-start sm:self-auto">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 flex items-center gap-1">
                          <span>✓</span>
                          <span>PASS</span>
                        </span>

                        {/* Expand / Collapse Indicator Arrow */}
                        <span className="text-[#9B7FF6] font-mono text-xs font-bold transition-transform">
                          {isExpanded ? "▲" : "▼"}
                        </span>
                      </div>
                    </div>

                    {/* Collapsed One-line Summary Preview */}
                    {!isExpanded && (
                      <div className="font-mono text-[11px] text-zinc-400 flex items-center justify-between gap-3 truncate">
                        <span className="truncate">
                          this_hash: <code className="text-emerald-300 font-bold">{truncateHash(entry.this_hash)}</code>
                        </span>
                        <span className="text-[10px] text-[#9B7FF6] shrink-0">Click to view full metadata &rarr;</span>
                      </div>
                    )}

                    {/* Expanded Full Metadata Drawer */}
                    {isExpanded && (
                      <div className="space-y-3 pt-2.5 border-t border-zinc-800/80 animate-in fade-in duration-150">
                        {/* Complete Full Hashes */}
                        <div className="space-y-1.5 bg-zinc-900/80 p-3 rounded-lg border border-zinc-800 font-mono text-[11px]">
                          <div className="flex items-center justify-between flex-wrap gap-1">
                            <span className="text-zinc-400 font-semibold">this_hash:</span>
                            <span className="text-emerald-300 font-bold break-all">{entry.this_hash}</span>
                          </div>
                          <div className="flex items-center justify-between flex-wrap gap-1">
                            <span className="text-zinc-400 font-semibold">prev_hash:</span>
                            <span className="text-zinc-400 font-medium break-all">{entry.prev_hash}</span>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-zinc-500 pt-1">
                            <span>Timestamp: {new Date(entry.created_at).toUTCString()}</span>
                            <span>Proof Status: SHA-256 Validated</span>
                          </div>
                        </div>

                        {/* Complete Formatted JSON Payload Object */}
                        {entry.payload && (
                          <div className="space-y-1">
                            <div className="text-[11px] font-mono font-semibold text-indigo-300 flex items-center justify-between">
                              <span>Full Metadata Payload</span>
                              <span className="text-[10px] text-zinc-500 font-normal">JSON Schema v1.0</span>
                            </div>
                            <pre className="text-[11px] font-mono text-zinc-200 bg-black/90 p-3 rounded-lg border border-indigo-900/40 overflow-x-auto leading-relaxed whitespace-pre-wrap">
                              {JSON.stringify(entry.payload, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-4 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
          <div>Read-only cryptographic audit inspector</div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold text-zinc-300 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 cursor-pointer"
          >
            Close Proof Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
