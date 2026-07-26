export type Severity = "high" | "medium" | "low";

export type EvidenceScope = "org_wide" | "model" | "actor" | "industry_general";

export interface Finding {
  finding_id: string;
  model_id: string;
  model_name: string;
  severity: Severity;
  validated: boolean;
  evidence_scope: EvidenceScope;
  evidence_label: string;
  routed_to_team?: string | null;
  severity_multiplier?: number;
  tag_source?: string;
  tag_source_label?: string;
  status: string;
  actor?: string;
  node_type?: string;
  event_timestamp?: string | null;
  summary: string;
  recommended_action?: string;
  written_back?: boolean;
  created_at?: string | null;
}

export interface GroupedModelFinding {
  model_id: string;
  primaryFinding: Finding;
  additionalCount: number;
}
