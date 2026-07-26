/**
 * Unified Varve API Client & Endpoint Connector
 * Centralizes all frontend-to-backend FastAPI calls (100% backend driven).
 */

import { Finding } from "@/components/triage/types";
import { CandidateIncident } from "@/components/triage/PendingReviewPanel";
import { LedgerEntryRow } from "@/components/triage/AuditModal";
import { ActorHistoryResponse } from "@/components/triage/ActorHistoryBoard";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Helper for default headers
const defaultHeaders = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

export interface StepResult {
  ok: boolean;
  step: string;
  label: string;
  detail: string;
  error?: string;
}

/**
 * 1. Fetch Risk Rankings for Screen 1 Triage Board (GET /models/risk-ranking)
 */
export async function fetchRiskRankings(): Promise<Finding[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/models/risk-ranking`, {
      headers: defaultHeaders,
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data: Finding[] = await res.json();
    return data;
  } catch (err) {
    console.warn("API Error in fetchRiskRankings:", err);
    return [];
  }
}

/**
 * 2. Fetch Finding Detail for Screen 2 (GET /findings/{finding_id})
 */
export async function fetchFindingDetail(findingId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/findings/${findingId}`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

/**
 * 3. Fetch Pending Candidate Incidents for Screen 1 (GET /candidate-incidents)
 */
export async function fetchCandidateIncidents(): Promise<CandidateIncident[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/candidate-incidents`, {
      headers: defaultHeaders,
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.warn("API Error in fetchCandidateIncidents:", err);
    return [];
  }
}

/**
 * 4. Confirm Candidate Incident (POST /candidate-incidents/{id}/confirm)
 */
export async function confirmCandidateIncident(candidateId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/candidate-incidents/${candidateId}/confirm`, {
    method: "POST",
    headers: defaultHeaders,
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * 5. Dismiss Candidate Incident (POST /candidate-incidents/{id}/dismiss)
 */
export async function dismissCandidateIncident(candidateId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/candidate-incidents/${candidateId}/dismiss`, {
    method: "POST",
    headers: defaultHeaders,
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * 6. Run SHA-256 Ledger Chain Verification (GET /ledger/verify)
 */
export async function verifyLedgerChain(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/ledger/verify`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

/**
 * 7. Fetch Finding Ledger Entries (GET /ledger/findings/{findingId})
 */
export async function fetchLedgerEntriesForFinding(findingId: string): Promise<LedgerEntryRow[]> {
  const res = await fetch(`${API_BASE_URL}/ledger/findings/${findingId}`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  return data.entries || [];
}

/**
 * 8. Fetch Actor Cross-Model History for Screen 3 (GET /patterns/by-actor/{actor})
 */
export async function fetchActorHistoryData(actor: string): Promise<ActorHistoryResponse | null> {
  const res = await fetch(`${API_BASE_URL}/patterns/by-actor/${encodeURIComponent(actor)}`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

/**
 * 9. Real DataHub Connection Verification (POST /datahub/connect)
 */
export async function connectToDataHub(params: {
  gms_url: string;
  username?: string;
  password?: string;
  actor_name?: string;
  actor_initials?: string;
}): Promise<{
  connected: boolean;
  gms_url: string;
  status: string;
  latency_ms: number;
  message: string;
  identity: { name: string; initials: string; role: string };
}> {
  const res = await fetch(`${API_BASE_URL}/datahub/connect`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

/**
 * 10. Execute individual real DataHub connection step
 */
export async function executeConnectionStep(
  stepKey: "gms" | "lineage" | "ownership" | "governance" | "incidents",
  params: { gms_url: string; username?: string; password?: string }
): Promise<StepResult> {
  const res = await fetch(`${API_BASE_URL}/datahub/connect/step/${stepKey}`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  return {
    ok: data.ok !== false,
    step: stepKey,
    label: data.label,
    detail: data.detail,
    error: data.error,
  };
}

/**
 * 11. Trigger DataHub Writeback for Finding (POST /findings/{finding_id}/writeback)
 */
export async function triggerWriteback(findingId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/findings/${findingId}/writeback`, {
    method: "POST",
    headers: defaultHeaders,
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

export function getRelativeTimeString(dateInput: string | Date | number): string {
  if (!dateInput) return "just now";
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return String(dateInput);
  const now = new Date();
  const diffSec = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000));
  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}
