"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { executeConnectionStep, StepResult } from "@/lib/api";
import Navbar from "@/components/Navbar";

type StepKey = "gms" | "lineage" | "ownership" | "governance" | "incidents";

interface StepState {
  key: StepKey;
  label: string;
  status: "idle" | "pending" | "success" | "error";
  detail?: string;
  errorMsg?: string;
}

const INITIAL_STEPS: StepState[] = [
  {
    key: "gms",
    label: "Connecting to DataHub GMS...",
    status: "idle",
  },
  {
    key: "lineage",
    label: "Reading lineage graph...",
    status: "idle",
  },
  {
    key: "ownership",
    label: "Resolving ownership metadata...",
    status: "idle",
  },
  {
    key: "governance",
    label: "Checking governance tags...",
    status: "idle",
  },
  {
    key: "incidents",
    label: "Loading incident history...",
    status: "idle",
  },
];

export default function ConnectPage() {
  const router = useRouter();

  // Form Fields (Section 2 Spec)
  const [gmsUrl, setGmsUrl] = useState<string>("http://localhost:8080");
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");

  // Connection Workflow State
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepState[]>(INITIAL_STEPS);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [isComplete, setIsComplete] = useState<boolean>(false);

  // Compute identity initials for top-bar avatar on Screen 1
  const computeInitials = (nameStr: string) => {
    const parts = nameStr.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    } else if (parts[0].length >= 2) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return "IC";
  };

  const runConnectionSequence = async (startIndex: number = 0) => {
    setIsSubmitting(true);
    let currentSteps = [...steps];

    for (let i = startIndex; i < INITIAL_STEPS.length; i++) {
      const stepKey = INITIAL_STEPS[i].key;
      setActiveStepIndex(i);

      // Set current step to pending
      currentSteps = currentSteps.map((s, idx) =>
        idx === i ? { ...s, status: "pending" } : s
      );
      setSteps(currentSteps);

      try {
        // Execute real backend HTTP step check (Section 3 Spec)
        const result: StepResult = await executeConnectionStep(stepKey, {
          gms_url: gmsUrl,
          username,
          password,
        });

        if (result.ok) {
          // If Step 5 (incidents) has zero history, detail displays honest cold-start line:
          // "No organizational incident history found — industry baseline will be used"
          currentSteps = currentSteps.map((s, idx) =>
            idx === i
              ? {
                  ...s,
                  status: "success",
                  label: stepKey === "incidents" && result.detail.includes("No organizational incident history")
                    ? "No organizational incident history found — industry baseline will be used"
                    : s.label,
                  detail: result.detail,
                }
              : s
          );
          setSteps(currentSteps);
        } else {
          // Step genuine failure state (e.g. Invalid DataHub credentials)
          const errText = result.error || "Invalid DataHub credentials";
          setFormError(errText);
          currentSteps = currentSteps.map((s, idx) =>
            idx === i
              ? {
                  ...s,
                  status: "error",
                  errorMsg: errText,
                }
              : s
          );
          setSteps(currentSteps);
          setIsSubmitting(false);
          setActiveStepIndex(-1); // Return form to visible state with error banner
          return; // Stop sequence on error for user correction
        }
      } catch (err: any) {
        const errText = err.message || "Backend network request failed.";
        setFormError(errText);
        currentSteps = currentSteps.map((s, idx) =>
          idx === i
            ? {
                ...s,
                status: "error",
                errorMsg: errText,
              }
            : s
        );
        setSteps(currentSteps);
        setIsSubmitting(false);
        setActiveStepIndex(-1);
        return;
      }
    }

    // All steps succeeded
    setIsSubmitting(false);
    setIsComplete(true);

    // Store minimal identity info in localStorage for Screen 1 top-bar avatar (Section 4 Spec)
    const displayName = username === "datahub" || username === "varve" ? "Ian Chen" : username;
    const initials = computeInitials(displayName);
    const identityObj = {
      username,
      name: displayName,
      initials,
      role: "ML Platform Lead",
    };
    try {
      localStorage.clear();
      localStorage.setItem("varve_user_identity", JSON.stringify(identityObj));
    } catch {
      // localStorage fallback
    }

    // Hold briefly (~500ms) on fully-checked list then transition to Screen 1 (/triage)
    setTimeout(() => {
      router.push("/triage");
    }, 500);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSteps(INITIAL_STEPS);
    setIsComplete(false);
    runConnectionSequence(0);
  };

  const handleRetryStep = (failedIndex: number) => {
    runConnectionSequence(failedIndex);
  };

  return (
    <div className="min-h-screen bg-[#050507] text-zinc-100 font-sans flex flex-col selection:bg-[#9B7FF6] selection:text-white antialiased relative overflow-hidden">
      {/* Landing Navbar */}
      <Navbar />

      {/* Background Ambient Glow — large outer ring */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-[#9B7FF6]/8 rounded-full blur-[160px] pointer-events-none" />

      {/* Background Ambient Glow — tighter inner ring behind card */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[380px] h-[380px] bg-[#9B7FF6]/15 rounded-full blur-[90px] pointer-events-none" />

      {/* Main Centered Connect Card */}
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
        <main className="w-full max-w-md p-8 sm:p-10 rounded-2xl border border-white/10 bg-zinc-950/80 backdrop-blur-2xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9),_inset_0_1px_0_0_rgba(255,255,255,0.12)] flex flex-col items-center text-center space-y-6">
        
        {/* Top Logo & Short Tagline */}
        <div className="flex flex-col items-center space-y-3">
          <Image
            src="/varve_clean.png"
            alt="Varve Logo"
            width={145}
            height={35}
            className="h-7 sm:h-8 w-auto object-contain"
            priority
          />
          <p className="text-xs sm:text-sm text-zinc-400 font-normal max-w-xs leading-relaxed">
            Tells you which of your production ML models will break next
          </p>
        </div>

        {/* SECTION 2 — 2-Field Credentials Form */}
        <form onSubmit={handleSubmit} className="w-full space-y-4 text-left pt-2">
          {/* Field 1: DataHub Instance URL */}
          <div>
            <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
              DataHub Instance URL
            </label>
            <input
              type="text"
              value={gmsUrl}
              disabled={isSubmitting}
              onChange={(e) => setGmsUrl(e.target.value)}
              placeholder="http://localhost:8080"
              required
              className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#9B7FF6] focus:ring-1 focus:ring-[#9B7FF6] transition-all disabled:opacity-50"
            />
          </div>

          {/* Field 2: Credentials Group (Username / Password) */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                disabled={isSubmitting}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="varve"
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#9B7FF6] focus:ring-1 focus:ring-[#9B7FF6] transition-all disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                disabled={isSubmitting}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="varve"
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#9B7FF6] focus:ring-1 focus:ring-[#9B7FF6] transition-all disabled:opacity-50"
              />
            </div>
          </div>

          {/* Real DataHub Authentication Error Banner */}
          {formError && (
            <div className="p-3.5 rounded-xl bg-rose-950/80 border border-rose-500/40 text-rose-300 text-xs font-mono flex items-start gap-2.5 animate-in fade-in duration-200">
              <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0 mt-1 animate-ping" />
              <div className="flex-1">
                <strong className="block text-rose-200 font-bold mb-0.5">Authentication Failed</strong>
                <span>{formError} — check your DataHub URL & credentials.</span>
              </div>
            </div>
          )}

          {/* Submit Action Button with Active Loader */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full relative group inline-flex items-center justify-center gap-2 px-6 py-3.5 mt-2 rounded-xl font-semibold text-xs text-white transition-all cursor-pointer select-none border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl shadow-[inset_0_1px_0_0_rgba(255,255,255,0.2),_0_4px_20px_-2px_rgba(0,0,0,0.6),_0_0_15px_-3px_rgba(155,127,246,0.25)] hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.35),_0_6px_25px_-2px_rgba(0,0,0,0.8),_0_0_22px_-2px_rgba(155,127,246,0.4)] hover:border-white/25 active:translate-y-[1px] disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <span className="w-4 h-4 rounded-full border-2 border-white/20 border-t-[#9B7FF6] animate-spin" />
                <span>Connecting to DataHub...</span>
              </>
            ) : (
              <>
                <span>Connect to DataHub</span>
                <span className="text-[#9B7FF6] group-hover:translate-x-0.5 transition-transform">&rarr;</span>
              </>
            )}
          </button>
        </form>

        {/* SECTION 3 — Live Step-by-Step Connection Sequence */}
        {(isSubmitting || activeStepIndex >= 0) && (
          <div className="w-full space-y-3.5 text-left pt-2">
            <div className="text-[11px] font-semibold tracking-wider text-[#9B7FF6] uppercase flex items-center justify-between pb-1 border-b border-white/10">
              <span>Establishing Live System Connection</span>
              {isComplete && (
                <span className="text-emerald-400 font-mono text-[10px]">Verified ✓</span>
              )}
            </div>

            <div className="space-y-3">
              {steps.map((st, idx) => (
                <div
                  key={st.key}
                  className={`p-3 rounded-xl border transition-all text-xs flex flex-col gap-1 ${
                    st.status === "pending"
                      ? "bg-zinc-900/90 border-[#9B7FF6]/40 text-zinc-200 shadow-[0_0_15px_rgba(155,127,246,0.15)]"
                      : st.status === "success"
                      ? "bg-zinc-900/50 border-emerald-500/20 text-zinc-300"
                      : st.status === "error"
                      ? "bg-rose-950/60 border-rose-500/40 text-rose-200"
                      : "bg-zinc-950/40 border-white/5 text-zinc-500 opacity-60"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      {/* Step Status Indicator Icon */}
                      {st.status === "pending" && (
                        <span className="w-3.5 h-3.5 rounded-full border-2 border-[#9B7FF6] border-t-transparent animate-spin shrink-0" />
                      )}
                      {st.status === "success" && (
                        <span className="w-4 h-4 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-bold text-[10px] flex items-center justify-center shrink-0">
                          ✓
                        </span>
                      )}
                      {st.status === "error" && (
                        <span className="w-4 h-4 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-400 font-bold text-[10px] flex items-center justify-center shrink-0">
                          ✕
                        </span>
                      )}
                      {st.status === "idle" && (
                        <span className="w-3.5 h-3.5 rounded-full border border-zinc-700 shrink-0" />
                      )}

                      <span className="font-mono font-medium">
                        {st.label}
                      </span>
                    </div>

                    {/* Retry Button for Failed Step */}
                    {st.status === "error" && (
                      <button
                        onClick={() => handleRetryStep(idx)}
                        className="px-2 py-0.5 rounded bg-rose-900/60 hover:bg-rose-800 text-[10px] font-mono text-rose-200 border border-rose-500/30 transition-all cursor-pointer"
                      >
                        Retry
                      </button>
                    )}
                  </div>

                  {/* Real Backend Detail Output */}
                  {st.detail && (
                    <div className="pl-6 font-mono text-[11px] text-zinc-400">
                      {"└ "}{st.detail}
                    </div>
                  )}

                  {/* Error Detail Message */}
                  {st.errorMsg && (
                    <div className="pl-6 font-mono text-[11px] text-rose-400">
                      {"└ Error: "}{st.errorMsg}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Transition Indicator */}
            {isComplete && (
              <div className="pt-2 text-center text-xs font-mono text-emerald-400 animate-pulse">
                Connection verified — entering dashboard...
              </div>
            )}
          </div>
        )}
        </main>
      </div>
    </div>
  );
}
