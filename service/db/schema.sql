-- Varve — Tier 1 schema

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ============================================================
-- lineage_events
-- Every change Varve has observed in a model's DataHub lineage.
-- ============================================================
CREATE TABLE lineage_events (
    event_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id                 TEXT NOT NULL,          -- DataHub urn of the affected model/dataset
    node_type                TEXT NOT NULL,          -- 'feature' | 'threshold' | 'pipeline_step' | 'retrain' | 'deployment'
    node_urn                 TEXT NOT NULL,          -- the specific DataHub node this event touched
    event_type               TEXT NOT NULL,          -- 'added' | 'modified' | 'removed' | 'retrained'
    event_timestamp          TIMESTAMPTZ NOT NULL,
    actor                    TEXT,                   -- engineer or system that made the change, if known
    actor_departed_within_90d BOOLEAN NOT NULL DEFAULT FALSE, -- Tier 2: departure flag within 90 days
    documentation_present     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_lineage_events_model_id ON lineage_events (model_id);
CREATE INDEX idx_lineage_events_actor ON lineage_events (actor);
CREATE INDEX idx_lineage_events_timestamp ON lineage_events (event_timestamp);


-- ============================================================
-- business_metrics
-- Time series checked against lineage events to detect anomalies
-- that precede reactive fixes, or improvement after a change.
-- ============================================================
CREATE TABLE business_metrics (
    metric_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id      TEXT NOT NULL,
    metric_name   TEXT NOT NULL,     -- e.g. 'accuracy', 'churn_rate'
    value         NUMERIC NOT NULL,
    is_anomaly    BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at   TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_business_metrics_model_id ON business_metrics (model_id);
CREATE INDEX idx_business_metrics_recorded_at ON business_metrics (recorded_at);
CREATE INDEX idx_business_metrics_is_anomaly ON business_metrics (is_anomaly);


-- ============================================================
-- incidents
-- The organization's own incident history. This is what makes
-- Varve's findings "validated" rather than generic pattern-matching.
-- ============================================================
CREATE TABLE incidents (
    incident_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id            TEXT NOT NULL,          -- the model that actually broke
    detected_at         TIMESTAMPTZ NOT NULL,
    resolved_at         TIMESTAMPTZ,
    root_cause_event_id UUID REFERENCES lineage_events(event_id),
    -- ^ the event that, in hindsight, caused this incident.
    --   May belong to a DIFFERENT model_id than the one that failed --
    --   that's what makes cross-model correlation possible in Tier 2.
    description         TEXT,
    fix_summary          TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_incidents_model_id ON incidents (model_id);
CREATE INDEX idx_incidents_root_cause_event_id ON incidents (root_cause_event_id);


-- ============================================================
-- patterns (Tier 2 Org-Wide Rollup Table)
-- Aggregates pattern occurrences by scope (model_id, actor, or 'org_wide')
-- ============================================================
CREATE TABLE patterns (
    pattern_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type           TEXT NOT NULL,          -- 'departing_engineer_change' | 'stale_threshold' | 'orphaned_experiment' | 'reactive_fix'
    scope_key              TEXT NOT NULL,          -- model_id URN, actor name (e.g. 'J. Alvarez'), 'org_wide', or 'industry_general'
    times_observed         INTEGER NOT NULL DEFAULT 0,
    times_preceded_incident INTEGER NOT NULL DEFAULT 0,
    avg_detection_lag_days NUMERIC DEFAULT 0,
    last_updated           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT unique_scope_pattern UNIQUE (scope_key, pattern_type)
);

CREATE INDEX idx_patterns_scope_key ON patterns (scope_key);
CREATE INDEX idx_patterns_type ON patterns (pattern_type);


-- ============================================================
-- findings
-- The output artifact: what gets shown in the UI and written
-- back to DataHub.
-- ============================================================
CREATE TABLE findings (
    finding_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id            TEXT NOT NULL,
    related_event_id    UUID REFERENCES lineage_events(event_id),
    severity            TEXT NOT NULL DEFAULT 'medium',  -- 'high' | 'medium' | 'low'
    validated           BOOLEAN NOT NULL DEFAULT FALSE,   -- true if a real incident precedent was found
    evidence_scope      TEXT NOT NULL DEFAULT 'org_wide', -- 'model' | 'actor' | 'org_wide' | 'industry_general'
    routed_to_team      TEXT NOT NULL DEFAULT 'Ian Chen', -- auto-routed owner resolved from DataHub ownership aspect
    narrative            TEXT,                             -- Claude-generated explanation
    recommended_action   TEXT,                             -- Claude-generated
    status               TEXT NOT NULL DEFAULT 'open',     -- 'open' | 'reviewed' | 'resolved' | 'dismissed'
    written_back_at       TIMESTAMPTZ,                      -- null until write-back to DataHub completes
    datahub_annotation_urn TEXT,                             -- DataHub metadata aspect reference
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_findings_model_id ON findings (model_id);
CREATE INDEX idx_findings_severity ON findings (severity);
CREATE INDEX idx_findings_status ON findings (status);
CREATE INDEX idx_findings_evidence_scope ON findings (evidence_scope);
CREATE INDEX idx_findings_routed_to_team ON findings (routed_to_team);


-- ============================================================
-- ledger (Phase B Audit Ledger)
-- Append-only cryptographic hash chain for finding decisions.
-- ============================================================
CREATE TABLE ledger (
    ledger_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type    TEXT NOT NULL,   -- 'finding_created' | 'severity_set' | 'downgrade' | 'writeback' | 'incident_confirmed' | 'incident_dismissed'
    finding_id    UUID REFERENCES findings(finding_id),
    payload       JSONB NOT NULL,  -- whatever's relevant to this event type
    prev_hash     TEXT,            -- hash of the previous row, null for the first row
    this_hash     TEXT NOT NULL,   -- sha256(prev_hash + event_type + finding_id + payload + created_at)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_finding_id ON ledger (finding_id);
CREATE INDEX idx_ledger_created_at ON ledger (created_at);


-- ============================================================
-- candidate_incidents (Phase D2.3 - D2.5 Candidate Incident Discovery)
-- ============================================================
CREATE TABLE candidate_incidents (
    candidate_id         TEXT PRIMARY KEY,
    model_id            TEXT NOT NULL,
    anomaly_metric      TEXT NOT NULL,
    anomaly_value       NUMERIC NOT NULL,
    anomaly_date        TIMESTAMPTZ NOT NULL,
    candidate_event_id  UUID REFERENCES lineage_events(event_id),
    days_between        NUMERIC NOT NULL,
    status              TEXT NOT NULL DEFAULT 'unconfirmed', -- 'unconfirmed' | 'confirmed' | 'dismissed'
    proposed_description TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_candidate_incidents_status ON candidate_incidents (status);


-- ============================================================
-- Sanity check: confirm every table exists and is empty
-- ============================================================
SELECT 'lineage_events' AS table_name, count(*) FROM lineage_events
UNION ALL
SELECT 'business_metrics', count(*) FROM business_metrics
UNION ALL
SELECT 'incidents', count(*) FROM incidents
UNION ALL
SELECT 'patterns', count(*) FROM patterns
UNION ALL
SELECT 'findings', count(*) FROM findings
UNION ALL
SELECT 'ledger', count(*) FROM ledger;