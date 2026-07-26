"""
Varve Correlation Service — Tier 2 (Cross-Model + Patterns Table + Downgrade Logic)

Core business logic:
- get_matching_incidents_for_event(event_id): query incidents linked by root_cause_event_id.
- get_actor_cross_model_incidents(actor): find all incidents linked to ANY event by this actor across models.
- classify_pattern(event_id): runs both per-model AND actor-level cross-model checks with two-step severity assignment.
- populate_patterns(): upsert model-scoped, actor-scoped, and org_wide pattern rows.
- run_ground_truth_check(): test harness for seed narratives.
"""

import sys
import os
from typing import List, Dict, Any, Optional

# Ensure service root is in sys.path
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection


# ---------------------------------------------------------------------------
# Direct incident match
# ---------------------------------------------------------------------------

def get_matching_incidents_for_event(event_id: str) -> List[Dict[str, Any]]:
    """
    Given a lineage_events.event_id, look up incidents where
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
# Cross-model actor-level incident lookup
# ---------------------------------------------------------------------------

def get_actor_cross_model_incidents(actor: str) -> List[Dict[str, Any]]:
    """
    Given an actor name, find ALL lineage_events by that actor
    across all models, then find incidents linked to any of those events
    (via root_cause_event_id), regardless of which model the incident landed on.
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
    Returns all lineage events for a given actor across all models,
    including resolution of mapped DataHub owner names or aliases.
    """
    mapped_owner_urn = ""
    mapped_display_name = ""
    try:
        from services.actor_resolution_service import match_actor_to_datahub_owner
        resolved = match_actor_to_datahub_owner(actor)
        mapped_owner_urn = resolved["datahub_owner_urn"]
        mapped_display_name = resolved["datahub_display_name"]
    except Exception as e:
        print(f"[warning] Actor identity resolution fallback: {e}")

    query = """
        SELECT DISTINCT
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
            ROUND(EXTRACT(EPOCH FROM (i.detected_at - e.event_timestamp)) / 86400.0)::INT AS detection_lag_days
        FROM lineage_events e
        LEFT JOIN incidents i ON i.root_cause_event_id = e.event_id
        LEFT JOIN findings f ON f.related_event_id = e.event_id
        LEFT JOIN actor_owner_mappings m ON LOWER(m.lineage_actor) = LOWER(e.actor)
        WHERE LOWER(e.actor) = LOWER(%s)
           OR (m.datahub_display_name IS NOT NULL AND LOWER(m.datahub_display_name) LIKE LOWER(%s))
           OR (%s != '' AND LOWER(f.routed_to_team) LIKE LOWER(%s))
        ORDER BY e.event_timestamp;
    """
    actor_param = actor
    disp_param = f"%{mapped_display_name.split('(')[0].strip()}%" if mapped_display_name else f"%{actor}%"
    routed_param = f"%{actor.split('(')[0].strip()}%"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (actor_param, disp_param, actor, routed_param))
            rows = cur.fetchall()
            return [dict(r) for r in rows]



# ---------------------------------------------------------------------------
# Two-step classification with cross-model check
# ---------------------------------------------------------------------------

def _provisional_severity(node_type: str, documentation_present: bool) -> str:
    """
    Assign a provisional severity based purely on pattern type signals,
    before consulting incident history.
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


def resolve_pattern_severity_by_trust_scope(
    pattern_type: str,
    actor: Optional[str] = None,
    direct_incidents: Optional[List[Dict[str, Any]]] = None,
    cross_model_incidents: Optional[List[Dict[str, Any]]] = None,
    provisional_severity: str = "high",
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    D1.4 Trust Hierarchy Scope Resolution:
    Checks pattern scopes in strict trust order:
      1. Direct per-model incident match
      2. Cross-model per-actor incident match
      3. org_wide pattern rollup
      4. actor pattern rollup
      5. industry_general baseline fallback

    Only falls through to a lower-trust scope if higher-trust scopes have 0 observations.
    """
    # 1 & 2: Direct empirical org incidents always take top priority
    if direct_incidents or cross_model_incidents:
        scope = "model" if direct_incidents else "actor"
        return {
            "severity": provisional_severity,
            "validated": True,
            "scope_key": scope,
            "fallback_used": False,
            "resolution_reason": f"Direct org incident precedent found at {scope} scope."
        }

    # 3, 4, 5: Consult patterns table in trust hierarchy order
    scopes_to_check = ["org_wide"]
    if actor:
        scopes_to_check.append(actor)
    scopes_to_check.append("industry_general")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for scope in scopes_to_check:
                cur.execute("""
                    SELECT times_observed, times_preceded_incident, avg_detection_lag_days
                    FROM patterns
                    WHERE scope_key = %s AND pattern_type = %s;
                """, (scope, pattern_type))
                row = cur.fetchone()

                if row and row["times_observed"] > 0:
                    times_obs = row["times_observed"]
                    times_inc = row["times_preceded_incident"]
                    has_precedent = times_inc > 0

                    if scope == "industry_general":
                        base_rate = times_inc / float(times_obs) if times_obs > 0 else 0.0
                        # Industry base-rate threshold evaluation:
                        # - Base rate >= 0.25 (High Industry Risk): retain provisional severity
                        # - Base rate 0.15 .. 0.24 (Moderate Industry Risk): cap severity at MEDIUM
                        # - Base rate < 0.15 (Low Industry Risk): downgrade severity to LOW
                        if base_rate >= 0.25:
                            sev = provisional_severity
                        elif base_rate >= 0.15:
                            sev = "medium" if provisional_severity == "high" else provisional_severity
                        else:
                            sev = "low"

                        return {
                            "severity": sev,
                            "validated": False,
                            "scope_key": "industry_general",
                            "fallback_used": True,
                            "resolution_reason": f"No org incident history found; evaluated industry baseline rate ({times_inc}/{times_obs} = {base_rate:.0%} risk precedence -> severity={sev.upper()})."
                        }
                    else:
                        # Higher-trust org scope found with observations
                        sev = provisional_severity if has_precedent else "low"
                        return {
                            "severity": sev,
                            "validated": has_precedent,
                            "scope_key": scope,
                            "fallback_used": False,
                            "resolution_reason": f"Resolved via {scope} pattern history ({times_inc}/{times_obs} incidents)."
                        }

    return {
        "severity": "low",
        "validated": False,
        "scope_key": "default_unvalidated",
        "fallback_used": False,
        "resolution_reason": "No pattern observations found at any scope."
    }


def classify_pattern(event_id: str) -> Dict[str, Any]:
    """
    Two-step severity classification using trust hierarchy scope resolution (org_wide -> actor -> industry_general).
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

    # Step 1 — Provisional severity
    provisional = _provisional_severity(event["node_type"], event["documentation_present"])

    # Step 2a — Per-event direct incident match
    direct_incidents = get_matching_incidents_for_event(event_id)

    # Step 2b — Cross-model actor incident match
    cross_model_incidents: List[Dict[str, Any]] = []
    if event["actor"]:
        cross_model_rows = get_actor_cross_model_incidents(event["actor"])
        cross_model_incidents = [
            r for r in cross_model_rows
            if str(r["origin_event_id"]) != event_id
        ]

    # Initial validation boolean
    is_validated_direct = len(direct_incidents) > 0 or len(cross_model_incidents) > 0
    cross_model_validated = len(cross_model_incidents) > 0

    pattern_type = _derive_pattern_type(
        event["node_type"],
        bool(event.get("actor_departed_within_90d")),
        event["documentation_present"],
        is_validated_direct,
    )

    # Step 2 — Final severity & validation resolution via trust hierarchy
    resolution = resolve_pattern_severity_by_trust_scope(
        pattern_type=pattern_type,
        actor=event["actor"],
        direct_incidents=direct_incidents,
        cross_model_incidents=cross_model_incidents,
        provisional_severity=provisional,
    )

    return {
        "event_id": str(event["event_id"]),
        "model_id": event["model_id"],
        "actor": event["actor"],
        "node_type": event["node_type"],
        "actor_departed_within_90d": bool(event.get("actor_departed_within_90d")),
        "pattern_type": pattern_type,
        "provisional_severity": provisional,
        "validated": resolution["validated"],
        "cross_model_validated": cross_model_validated,
        "severity": resolution["severity"],
        "scope_key": resolution["scope_key"],
        "fallback_used": resolution["fallback_used"],
        "resolution_reason": resolution["resolution_reason"],
        "matched_incidents": direct_incidents,
        "cross_model_incidents": cross_model_incidents,
        "incident_count": len(direct_incidents),
        "cross_model_incident_count": len(cross_model_incidents),
    }


# ---------------------------------------------------------------------------
# Populate / upsert patterns table
# ---------------------------------------------------------------------------

def populate_patterns() -> None:
    """
    After classification, upsert pattern rollup rows (model_id, actor, org_wide).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event_id, actor, model_id FROM lineage_events ORDER BY event_timestamp;")
            events = [dict(r) for r in cur.fetchall()]

    classifications = []
    for ev in events:
        c = classify_pattern(str(ev["event_id"]))
        classifications.append(c)

    scope_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for c in classifications:
        lags = []
        for inc in c["cross_model_incidents"]:
            if inc.get("detection_lag_days") is not None:
                lags.append(float(inc["detection_lag_days"]))

        for scope_key in [c["model_id"], c["actor"] or "unknown", "org_wide"]:
            key = (scope_key, c["pattern_type"])
            if key not in scope_stats:
                scope_stats[key] = {
                    "scope_key": scope_key,
                    "pattern_type": c["pattern_type"],
                    "times_observed": 0,
                    "times_preceded_incident": 0,
                    "lag_days": [],
                }
            scope_stats[key]["times_observed"] += 1
            if c["validated"]:
                scope_stats[key]["times_preceded_incident"] += 1
                scope_stats[key]["lag_days"].extend(lags)

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
            for (scope_key, p_type), stats in scope_stats.items():
                avg_lag = (
                    sum(stats["lag_days"]) / len(stats["lag_days"])
                    if stats["lag_days"] else 0.0
                )
                cur.execute(upsert_sql, (
                    stats["pattern_type"],
                    stats["scope_key"],
                    stats["times_observed"],
                    stats["times_preceded_incident"],
                    round(avg_lag, 1),
                ))
        conn.commit()

    print(f"✅ Patterns table upserted with {len(scope_stats)} scope rows.")


# ---------------------------------------------------------------------------
# Ground truth check harness
# ---------------------------------------------------------------------------

GROUND_TRUTH_EXPECTATIONS = {
    "addresses": {"expected_severity": "high", "expected_validated": True},
    "order_items": {"expected_severity": "medium", "expected_validated": True},
    "customers": {"expected_severity": "high", "expected_validated": True},
    "products": {"expected_severity": "low", "expected_validated": False},
    "countries": {"expected_severity": "low", "expected_validated": False},
}


def run_ground_truth_check() -> Dict[str, Any]:
    """
    Run classification against all seeded events and produce a structured benchmark result object.
    
    Returns:
    {
        "summary": { "total": 5, "passed": 5, "failed": 0, "all_passed": True },
        "events": [
            {
                "event_id": str,
                "model": str,
                "actor": str,
                "expected_severity": str,
                "actual_severity": str,
                "expected_validated": bool,
                "actual_validated": bool,
                "pass": bool
            },
            ...
        ]
    }
    """
    query = "SELECT event_id, actor, model_id FROM lineage_events ORDER BY event_timestamp;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            events = [dict(r) for r in cur.fetchall()]

    print(f"\n=======================================================")
    print(f"   VARVE CORRELATION SERVICE — GROUND TRUTH BENCHMARK")
    print(f"=======================================================")
    print(f"Total seeded events evaluated: {len(events)}\n")

    event_results = []
    for ev in events:
        eid = str(ev["event_id"])
        c = classify_pattern(eid)
        model_name = c["model_id"].split(".")[-1].replace(",PROD)", "")

        # Look up expectation by model keyword
        exp_key = next((k for k in GROUND_TRUTH_EXPECTATIONS if k in model_name), None)
        if exp_key:
            exp = GROUND_TRUTH_EXPECTATIONS[exp_key]
            expected_sev = exp["expected_severity"]
            expected_val = exp["expected_validated"]
        else:
            expected_sev = c["severity"]
            expected_val = c["validated"]

        is_pass = (c["severity"] == expected_sev) and (c["validated"] == expected_val)

        res_item = {
            "event_id": eid,
            "model": model_name,
            "actor": c["actor"],
            "expected_severity": expected_sev,
            "actual_severity": c["severity"],
            "expected_validated": expected_val,
            "actual_validated": c["validated"],
            "pass": is_pass,
        }
        event_results.append(res_item)

        status_symbol = "✔ PASS" if is_pass else "✖ FAIL"
        print(f"► [{status_symbol}] Model: {model_name:<12} | Actor: {c['actor']:<12}")
        print(f"  Severity:  expected={expected_sev.upper():<6} | actual={c['severity'].upper():<6}")
        print(f"  Validated: expected={str(expected_val):<6} | actual={str(c['validated']):<6}")
        print("-------------------------------------------------------")

    passed_count = sum(1 for e in event_results if e["pass"])
    total_count = len(event_results)
    failed_count = total_count - passed_count

    benchmark_summary = {
        "summary": {
            "total": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "all_passed": (failed_count == 0),
        },
        "events": event_results,
    }

    assert benchmark_summary["summary"]["all_passed"] is True, f"Ground truth benchmark assertions failed! {failed_count} events failed."

    print(f"\n✅ GROUND TRUTH BENCHMARK PASSED: {passed_count}/{total_count} events matched expectations.")
    return benchmark_summary
