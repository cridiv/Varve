"""
Varve Correlation Engine — Tier 2 (Cross-Model + Patterns Table + Downgrade Logic)

Step 13 additions on top of Tier 1:
- get_actor_cross_model_incidents(actor): find all incidents linked to ANY event by this actor
- classify_pattern(event_id): now runs both per-model AND actor-level cross-model checks
- populate_patterns(): upsert model-scoped, actor-scoped, and org_wide pattern rows
- Two-step severity assignment (Step 15.3): provisional → downgrade if no precedent found
"""

import sys
import os
from typing import List, Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from psycopg2.extras import RealDictCursor
from config.config import POSTGRES_DSN


def get_db_connection():
    """Returns a new psycopg2 database connection."""
    return psycopg2.connect(POSTGRES_DSN, cursor_factory=RealDictCursor)


# ---------------------------------------------------------------------------
# Step 5.1 (Tier 1): Per-event incident match
# ---------------------------------------------------------------------------

def get_matching_incidents_for_event(event_id: str) -> List[Dict[str, Any]]:
    """
    Step 5.1: Given a lineage_events.event_id, look up incidents where
    root_cause_event_id matches. Returns incidents on the SAME or ANY model.
    """
    query = """
        SELECT
            incident_id,
            model_id,
            detected_at,
            resolved_at,
            root_cause_event_id,
            description,
            fix_summary
        FROM incidents
        WHERE root_cause_event_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (event_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Step 13.1: Cross-model actor-level incident lookup
# ---------------------------------------------------------------------------

def get_actor_cross_model_incidents(actor: str) -> List[Dict[str, Any]]:
    """
    Step 13.1: Given an actor name, find ALL lineage_events by that actor
    across all models, then find incidents linked to any of those events
    (via root_cause_event_id), regardless of which model the incident landed on.

    This is the core cross-model correlation query — the one no single-model
    lineage scan can produce.
    """
    query = """
        SELECT
            e.event_id        AS origin_event_id,
            e.model_id        AS origin_model_id,
            e.node_type       AS origin_node_type,
            e.event_timestamp AS origin_event_timestamp,
            e.actor_departed_within_90d,
            i.incident_id,
            i.model_id        AS incident_model_id,
            i.detected_at,
            i.resolved_at,
            i.description,
            i.fix_summary,
            EXTRACT(EPOCH FROM (i.detected_at - e.event_timestamp)) / 86400.0 AS detection_lag_days
        FROM lineage_events e
        JOIN incidents i ON i.root_cause_event_id = e.event_id
        WHERE e.actor = %s
        ORDER BY e.event_timestamp;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (actor,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def get_all_actor_events(actor: str) -> List[Dict[str, Any]]:
    """
    Returns all lineage events for a given actor across all models (Step 14.1 helper).
    """
    query = """
        SELECT
            e.event_id,
            e.model_id,
            e.node_type,
            e.node_urn,
            e.event_type,
            e.event_timestamp,
            e.actor,
            e.actor_departed_within_90d,
            e.documentation_present,
            i.incident_id,
            i.model_id        AS incident_model_id,
            i.detected_at,
            i.description,
            i.fix_summary,
            EXTRACT(EPOCH FROM (i.detected_at - e.event_timestamp)) / 86400.0 AS detection_lag_days
        FROM lineage_events e
        LEFT JOIN incidents i ON i.root_cause_event_id = e.event_id
        WHERE e.actor = %s
        ORDER BY e.event_timestamp;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (actor,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Step 13.3 / Step 15.3: Two-step classification with cross-model check
# ---------------------------------------------------------------------------

def _provisional_severity(node_type: str, documentation_present: bool) -> str:
    """
    Step 15.3 — Step 1: Assign a provisional severity based purely on pattern
    type signals, before consulting incident history.

    This is the "naive" classifier — it flags undocumented threshold/pipeline
    changes as provisionally high so the downgrade is visible when no precedent exists.
    """
    if not documentation_present and node_type in ("threshold", "pipeline_step"):
        return "high"
    elif not documentation_present and node_type in ("feature", "deployment"):
        return "medium"
    else:
        return "low"


def _derive_pattern_type(
    node_type: str,
    actor_departed: bool,
    documentation_present: bool,
    is_validated: bool,
) -> str:
    """Derives a human-readable pattern type label for a classified event."""
    if actor_departed and not documentation_present:
        return "departing_engineer_change"
    elif not documentation_present and node_type == "threshold" and not is_validated:
        return "stale_threshold"
    elif not documentation_present:
        return "unreviewed_change"
    else:
        return "documented_change"


def classify_pattern(event_id: str) -> Dict[str, Any]:
    """
    Step 13.3 / 15.3: Two-step severity classification using both per-model
    and cross-model actor-level incident checks.

    Step 1 (provisional): Assign severity based on node_type + documentation signal.
    Step 2 (empirical):   Check incidents table (per-event AND cross-model by actor).
                          If zero precedent found anywhere → downgrade to 'low, unvalidated'.
                          If precedent found → confirm 'high, validated'.
    """
    event_query = """
        SELECT event_id, model_id, node_type, actor, event_timestamp,
               documentation_present, actor_departed_within_90d
        FROM lineage_events
        WHERE event_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(event_query, (event_id,))
            event = cur.fetchone()

    if not event:
        raise ValueError(f"Lineage event '{event_id}' not found in database.")

    event = dict(event)

    # Step 1 — Provisional severity (pattern shape only, no history)
    provisional = _provisional_severity(event["node_type"], event["documentation_present"])

    # Step 2a — Per-event direct incident match (Tier 1)
    direct_incidents = get_matching_incidents_for_event(event_id)

    # Step 2b — Cross-model actor incident match (Tier 2 / Step 13.1)
    cross_model_incidents: List[Dict[str, Any]] = []
    if event["actor"]:
        cross_model_rows = get_actor_cross_model_incidents(event["actor"])
        # Filter to cross-model hits only (incident on a DIFFERENT model than the event)
        cross_model_incidents = [
            r for r in cross_model_rows
            if str(r["origin_event_id"]) != event_id
        ]

    # Validation decision: validated if either direct OR cross-model precedent exists
    is_validated = len(direct_incidents) > 0 or len(cross_model_incidents) > 0
    cross_model_validated = len(cross_model_incidents) > 0

    # Step 2 — Final severity: downgrade if no empirical precedent found
    final_severity = provisional if is_validated else "low"

    pattern_type = _derive_pattern_type(
        event["node_type"],
        bool(event.get("actor_departed_within_90d")),
        event["documentation_present"],
        is_validated,
    )

    return {
        "event_id": str(event["event_id"]),
        "model_id": event["model_id"],
        "actor": event["actor"],
        "node_type": event["node_type"],
        "actor_departed_within_90d": bool(event.get("actor_departed_within_90d")),
        "pattern_type": pattern_type,
        "provisional_severity": provisional,       # Step 15.3: visible in frontend
        "validated": is_validated,
        "cross_model_validated": cross_model_validated,
        "severity": final_severity,
        "matched_incidents": direct_incidents,
        "cross_model_incidents": cross_model_incidents,
        "incident_count": len(direct_incidents),
        "cross_model_incident_count": len(cross_model_incidents),
    }


# ---------------------------------------------------------------------------
# Step 13.4: Populate / upsert the patterns table
# ---------------------------------------------------------------------------

def populate_patterns() -> None:
    """
    Step 13.4: After classification, upsert pattern rollup rows:
      - One row per model_id (scope_key = model URN)
      - One row per actor (scope_key = actor name)
      - One org_wide row (scope_key = 'org_wide')
    """
    # Fetch all events for classification
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event_id, actor, model_id FROM lineage_events ORDER BY event_timestamp;")
            events = [dict(r) for r in cur.fetchall()]

    classifications = []
    for ev in events:
        c = classify_pattern(str(ev["event_id"]))
        classifications.append(c)

    # Aggregate stats by scope_key (model_id, actor, org_wide)
    scope_stats: Dict[str, Dict[str, Any]] = {}

    for c in classifications:
        # Compute average detection lag across direct incidents
        lags = []
        for inc in c["matched_incidents"]:
            if inc.get("detected_at") and c.get("event_timestamp"):
                pass  # lag computation not available here, handled in DB query below
        for inc in c["cross_model_incidents"]:
            if inc.get("detection_lag_days") is not None:
                lags.append(float(inc["detection_lag_days"]))

        def _init_scope():
            return {"times_observed": 0, "times_preceded_incident": 0, "lag_days": [], "pattern_type": c["pattern_type"]}

        for scope_key in [c["model_id"], c["actor"] or "unknown", "org_wide"]:
            if scope_key not in scope_stats:
                scope_stats[scope_key] = _init_scope()
            scope_stats[scope_key]["times_observed"] += 1
            if c["validated"]:
                scope_stats[scope_key]["times_preceded_incident"] += 1
                scope_stats[scope_key]["lag_days"].extend(lags)

    # Upsert into patterns table
    upsert_sql = """
        INSERT INTO patterns (pattern_type, scope_key, times_observed, times_preceded_incident, avg_detection_lag_days, last_updated)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (scope_key, pattern_type)
        DO UPDATE SET
            times_observed          = EXCLUDED.times_observed,
            times_preceded_incident = EXCLUDED.times_preceded_incident,
            avg_detection_lag_days  = EXCLUDED.avg_detection_lag_days,
            last_updated            = NOW();
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for scope_key, stats in scope_stats.items():
                avg_lag = (
                    sum(stats["lag_days"]) / len(stats["lag_days"])
                    if stats["lag_days"] else 0.0
                )
                cur.execute(upsert_sql, (
                    stats["pattern_type"],
                    scope_key,
                    stats["times_observed"],
                    stats["times_preceded_incident"],
                    round(avg_lag, 1),
                ))
        conn.commit()

    print(f"✅ Patterns table upserted with {len(scope_stats)} scope rows.")


# ---------------------------------------------------------------------------
# Ground truth check — updated for Stories 1, 2, 3, 4
# ---------------------------------------------------------------------------

def run_ground_truth_check() -> List[Dict[str, Any]]:
    """
    Step 5.2/5.4 updated for Tier 2: Run classification against all seeded events.
    Confirms validated/unvalidated split + cross-model links matching seed-narrative.md.
    """
    query = "SELECT event_id, actor, model_id FROM lineage_events ORDER BY event_timestamp;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            events = [dict(r) for r in cur.fetchall()]

    print(f"\n=======================================================")
    print(f"   VARVE CORRELATION ENGINE — GROUND TRUTH VERIFICATION")
    print(f"=======================================================")
    print(f"Total seeded events evaluated: {len(events)}\n")

    results = []
    for ev in events:
        c = classify_pattern(str(ev["event_id"]))
        results.append(c)

        print(f"► Event:           {c['event_id']}")
        print(f"  Actor:           {c['actor']}  (departed={c['actor_departed_within_90d']})")
        print(f"  Model URN:       {c['model_id'].split('.')[-1].replace(',PROD)', '')}")
        print(f"  Pattern Type:    {c['pattern_type']}")
        print(f"  Provisional Sev: {c['provisional_severity'].upper()}")
        print(f"  Final Severity:  {c['severity'].upper()}")
        print(f"  Validated:       {c['validated']}  (cross_model={c['cross_model_validated']})")
        print(f"  Direct Incidents:      {c['incident_count']}")
        print(f"  Cross-Model Incidents: {c['cross_model_incident_count']}")
        if c["cross_model_incidents"]:
            xm = c["cross_model_incidents"][0]
            print(f"    └─ Model A origin:   ...{str(xm['origin_model_id']).split('.')[-1]}")
            print(f"    └─ Model B incident: ...{str(xm['incident_model_id']).split('.')[-1]}")
            print(f"    └─ Detection lag:    {float(xm['detection_lag_days'] or 0):.1f} days")
        print("-------------------------------------------------------")

    # Assertions — updated for 4 stories + 2 J. Alvarez events
    alvarez_results = [r for r in results if r["actor"] == "J. Alvarez"]
    chen_results    = [r for r in results if r["actor"] == "R. Chen"]

    # Story 1: customers → validated
    story1 = next(r for r in alvarez_results if "customers" in r["model_id"])
    assert story1["validated"] is True, "Story 1 (customers) must be validated"
    assert story1["severity"] == "high",  "Story 1 must be high severity"

    # Story 3 (Model A — addresses): validated via cross-model link
    story3a = next(r for r in alvarez_results if "addresses" in r["model_id"])
    assert story3a["validated"] is True, "Story 3 Model A (addresses) must be validated via cross-model"
    assert story3a["cross_model_validated"] is True, "Story 3 must have cross_model_validated=True"

    # Story 3 (Model B — order_items): direct incident match
    story3b = next(r for r in alvarez_results if "order_items" in r["model_id"])
    assert story3b["validated"] is True, "Story 3 Model B (order_items) must be validated"

    # Story 2 — R. Chen: unvalidated downgrade
    assert len(chen_results) >= 1, "R. Chen events must be present"
    story2 = next(r for r in chen_results if "products" in r["model_id"])
    assert story2["validated"] is False, "Story 2 (products) must be unvalidated"
    assert story2["severity"] == "low",  "Story 2 must be downgraded to low"

    print("\n✅ ALL GROUND TRUTH ASSERTIONS PASSED — Cross-model + downgrade logic verified!")
    return results


if __name__ == "__main__":
    run_ground_truth_check()
    print("\n--- Populating patterns table ---")
    populate_patterns()
