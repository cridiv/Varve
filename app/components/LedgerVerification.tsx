"use client";

import React, { useState } from "react";

interface LedgerBlock {
  blockNumber: number;
  action: string;
  targetModel: string;
  prevHash: string;
  hash: string;
  timestamp: string;
  status: "VERIFIED" | "PENDING";
}

const INITIAL_BLOCKS: LedgerBlock[] = [
  {
    blockNumber: 1043,
    action: "FINDING_GENERATED",
    targetModel: "fraud_model_v4",
    prevHash: "0a8f721b...99a1",
    hash: "b14e59d2...789d",
    timestamp: "2 mins ago",
    status: "VERIFIED",
  },
  {
    blockNumber: 1044,
    action: "SEVERITY_RESOLUTION",
    targetModel: "churn_model_v3",
    prevHash: "b14e59d2...789d",
    hash: "5c91a3e8...12ef",
    timestamp: "12 mins ago",
    status: "VERIFIED",
  },
  {
    blockNumber: 1045,
    action: "DATAHUB_WRITEBACK",
    targetModel: "new_signup_model",
    prevHash: "5c91a3e8...12ef",
    hash: "e83a64f0...90bc",
    timestamp: "45 mins ago",
    status: "VERIFIED",
  },
];

export default function LedgerVerification() {
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationPassed, setVerificationPassed] = useState(false);
  const [verifiedCount, setVerifiedCount] = useState(1045);

  const handleRunVerification = () => {
    setIsVerifying(true);
    setVerificationPassed(false);

    setTimeout(() => {
      setIsVerifying(false);
      setVerificationPassed(true);
      setVerifiedCount((prev) => prev + 1);
    }, 1800);
  };

  return (
    <section id="ledger" className="relative w-full max-w-7xl mx-auto px-6 py-20 border-t border-zinc-900">
      {/* Background Ambient Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-[#9B7FF6]/10 blur-[130px] rounded-full pointer-events-none z-0" />

      {/* Section Header */}
      <div className="relative z-10 flex flex-col items-center text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider text-[#9B7FF6] uppercase border border-[#9B7FF6]/25 bg-gradient-to-b from-[#9B7FF6]/15 via-zinc-900/60 to-zinc-950/80 backdrop-blur-md">
          <span>Zero Faith Required</span>
        </div>
        <h2 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl tracking-tight">
          Append-Only Audit Ledger
        </h2>
        <p className="text-zinc-400 max-w-2xl text-sm sm:text-base leading-relaxed">
          Every decision, severity resolution, downgrade, and DataHub write-back is hash-chained. Run <code className="text-[#9B7FF6] font-mono">verify_ledger.py</code> to prove history has never been altered.
        </p>
      </div>

      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        {/* Left Column: Interactive Terminal Simulator */}
        <div className="rounded-2xl border border-white/10 bg-black/80 backdrop-blur-xl overflow-hidden shadow-2xl">
          {/* Terminal Header */}
          <div className="px-4 py-3 bg-zinc-900/80 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500/80" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
            <span className="font-mono text-xs text-zinc-400">service/scripts/verify_ledger.py</span>
            <div className="w-12" />
          </div>

          {/* Terminal Content */}
          <div className="p-6 font-mono text-xs space-y-3 text-zinc-300 overflow-x-auto leading-relaxed">
            <div className="flex items-center gap-2 text-zinc-400">
              <span className="text-[#9B7FF6]">$</span>
              <span>python service/scripts/verify_ledger.py --db db/varve.db</span>
            </div>

            <div className="text-zinc-500 pt-1">
              [+] Walking {verifiedCount} hash-chained records...
            </div>

            <div className="space-y-1 pl-2 text-zinc-400">
              <div>[✓] Block 1043: SHA-256 match (0a8f72... -&gt; b14e59...)</div>
              <div>[✓] Block 1044: SHA-256 match (b14e59... -&gt; 5c91a3...)</div>
              <div>[✓] Block 1045: SHA-256 match (5c91a3... -&gt; e83a64...)</div>
            </div>

            {isVerifying ? (
              <div className="pt-2 text-[#9B7FF6] animate-pulse flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#9B7FF6] animate-ping" />
                <span>Scanning SHA-256 hash sequence...</span>
              </div>
            ) : verificationPassed ? (
              <div className="pt-2 text-emerald-400 font-semibold flex items-center gap-2">
                <span>[SUCCESS] All {verifiedCount} decisions verified intact. Zero tampering detected.</span>
              </div>
            ) : (
              <div className="pt-2 text-zinc-500">
                [Ready] Click verification trigger to walk chain live.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Animated Block Stream & Trigger */}
        <div className="space-y-6">
          <div className="space-y-4">
            {INITIAL_BLOCKS.map((block, idx) => (
              <div
                key={block.blockNumber}
                className={`relative p-5 rounded-xl border transition-all duration-300 ${
                  isVerifying
                    ? "border-[#9B7FF6]/50 bg-[#9B7FF6]/10"
                    : "border-white/10 bg-gradient-to-b from-zinc-900/60 to-zinc-950/80 backdrop-blur-md"
                }`}
              >
                {/* Connecting Laser Line */}
                {idx < INITIAL_BLOCKS.length - 1 && (
                  <div className="absolute left-7 -bottom-6 w-0.5 h-6 bg-gradient-to-b from-[#9B7FF6]/60 to-transparent z-10" />
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-[#9B7FF6] bg-[#9B7FF6]/15 px-2 py-1 rounded">
                      #{block.blockNumber}
                    </span>
                    <span className="text-sm font-semibold text-white">{block.action}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">{block.timestamp}</span>
                </div>

                <div className="mt-3 flex items-center justify-between text-xs text-zinc-400 font-mono">
                  <span>Target: <strong className="text-zinc-200">{block.targetModel}</strong></span>
                  <span className="text-[10px] text-zinc-500">Hash: {block.hash}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Verification Trigger Button */}
          <div className="pt-2 flex justify-start">
            <button
              onClick={handleRunVerification}
              disabled={isVerifying}
              className="relative group inline-flex items-center gap-3 px-8 py-4 rounded-xl font-semibold text-sm text-white transition-all cursor-pointer select-none border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl shadow-[inset_0_1px_0_0_rgba(255,255,255,0.2),_0_4px_20px_-2px_rgba(0,0,0,0.6)] hover:border-white/25 active:translate-y-[1px] disabled:opacity-50"
            >
              {isVerifying ? (
                <>
                  <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  <span>Verifying Ledger Chain...</span>
                </>
              ) : (
                <>
                  <span>Verify Ledger Integrity</span>
                  <span className="text-[#9B7FF6] group-hover:scale-110 transition-transform">✓</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
