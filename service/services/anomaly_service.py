"""
Varve Anomaly Service (D2.2)

Provides Z-score rolling metric anomaly detection across business_metrics.
Flags is_anomaly = True when a metric value falls > z_threshold standard deviations
away from historical baseline mean.
"""

import sys
import os
import math
from typing import Dict, Any, List

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection


def detect_metric_anomalies(z_threshold: float = 2.0) -> Dict[str, Any]:
    """
    Computes rolling mean and standard deviation for each (model_id, metric_name) series.
    Flags is_anomaly = True in PostgreSQL for metric points exceeding z_threshold.
    
    Returns structured summary of evaluated metric points and flagged anomalies.
    """
    query_series = """
        SELECT metric_id, model_id, metric_name, value, recorded_at
        FROM business_metrics
        ORDER BY model_id, metric_name, recorded_at ASC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_series)
            rows = [dict(r) for r in cur.fetchall()]

    # Group metrics by (model_id, metric_name)
    series_map: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["model_id"], r["metric_name"])
        if key not in series_map:
            series_map[key] = []
        series_map[key].append(r)

    total_scanned = 0
    anomalies_flagged: List[Dict[str, Any]] = []
    normal_points: List[str] = []

    for (model_id, metric_name), points in series_map.items():
        if len(points) < 2:
            # Need at least 2 points to compute standard deviation
            continue

        # Compute baseline statistics over historical points
        values = [float(p["value"]) for p in points]
        
        for i in range(len(points)):
            total_scanned += 1
            cur_point = points[i]
            val = float(cur_point["value"])

            # Use prior historical points as baseline window (or full series excluding cur if i==0)
            baseline = values[:i] if i >= 2 else values
            mean = sum(baseline) / len(baseline)
            variance = sum((x - mean) ** 2 for x in baseline) / (len(baseline) - 1 if len(baseline) > 1 else 1)
            stddev = math.sqrt(variance)

            # Evaluate Z-score
            if stddev > 0:
                z_score = abs(val - mean) / stddev
            else:
                z_score = 0.0

            is_anomaly = z_score >= z_threshold

            if is_anomaly:
                anomalies_flagged.append({
                    "metric_id": str(cur_point["metric_id"]),
                    "model_id": model_id,
                    "metric_name": metric_name,
                    "value": val,
                    "mean": round(mean, 2),
                    "stddev": round(stddev, 2),
                    "z_score": round(z_score, 2),
                    "recorded_at": cur_point["recorded_at"].isoformat() if cur_point["recorded_at"] else None
                })
            else:
                normal_points.append(str(cur_point["metric_id"]))

    # Update database is_anomaly flags
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if anomalies_flagged:
                anomaly_ids = [a["metric_id"] for a in anomalies_flagged]
                cur.execute("UPDATE business_metrics SET is_anomaly = TRUE WHERE metric_id = ANY(%s::uuid[]);", (anomaly_ids,))
            
            if normal_points:
                cur.execute("UPDATE business_metrics SET is_anomaly = FALSE WHERE metric_id = ANY(%s::uuid[]);", (normal_points,))
        conn.commit()

    print(f"✅ Anomaly detection scan completed: {total_scanned} points evaluated, {len(anomalies_flagged)} anomalies flagged (z_threshold >= {z_threshold}).")

    return {
        "total_scanned": total_scanned,
        "anomalies_count": len(anomalies_flagged),
        "z_threshold": z_threshold,
        "anomalies": anomalies_flagged,
    }


def find_candidate_incidents(lookback_days: int = 90) -> List[Dict[str, Any]]:
    """
    D2.3 Candidate Incident Discovery:
    For each flagged anomaly (is_anomaly = True), finds the nearest preceding lineage_events row
    within lookback_days.

    Constructs candidate objects:
    {
        "candidate_id": str,
        "model_id": str,
        "anomaly_metric": str,
        "anomaly_value": float,
        "anomaly_date": str,
        "candidate_event_id": str,
        "candidate_event_type": str,
        "candidate_node_type": str,
        "candidate_actor": str,
        "event_date": str,
        "days_between": float,
        "proposed_description": str
    }
    """
    # 1. Run anomaly detection scan first
    detect_metric_anomalies(z_threshold=2.0)

    # 2. Fetch all metric anomalies
    query_anomalies = """
        SELECT metric_id, model_id, metric_name, value, recorded_at
        FROM business_metrics
        WHERE is_anomaly = TRUE
        ORDER BY recorded_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_anomalies)
            anomalies = [dict(r) for r in cur.fetchall()]

    candidates = []

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for anom in anomalies:
                model_parts = anom["model_id"].split(".")
                table_keyword = model_parts[-1].replace(",PROD)", "").lower() if model_parts else ""

                query_event = """
                    SELECT event_id, model_id, node_type, event_type, actor, event_timestamp
                    FROM lineage_events
                    WHERE (
                        model_id = %s 
                        OR LOWER(model_id) LIKE %s
                    )
                    AND event_timestamp <= %s
                    AND event_timestamp >= (%s::timestamptz - (%s || ' days')::interval)
                    ORDER BY event_timestamp DESC
                    LIMIT 1;
                """
                cur.execute(query_event, (
                    anom["model_id"],
                    f"%{table_keyword}%",
                    anom["recorded_at"],
                    anom["recorded_at"],
                    lookback_days
                ))
                ev = cur.fetchone()

                if not ev:
                    fallback_event_query = """
                        SELECT event_id, model_id, node_type, event_type, actor, event_timestamp
                        FROM lineage_events
                        WHERE event_timestamp <= %s
                        AND event_timestamp >= (%s::timestamptz - (%s || ' days')::interval)
                        ORDER BY event_timestamp DESC
                        LIMIT 1;
                    """
                    cur.execute(fallback_event_query, (
                        anom["recorded_at"],
                        anom["recorded_at"],
                        lookback_days
                    ))
                    ev = cur.fetchone()

                if ev:
                    ev_dict = dict(ev)
                    recorded_dt = anom["recorded_at"]
                    event_dt = ev_dict["event_timestamp"]
                    days_between = round((recorded_dt - event_dt).total_seconds() / 86400.0, 1)

                    # Integrate Bounded Financial Risk Calculation
                    from services.datahub_service import resolve_dataset_financial_baseline
                    base_info = resolve_dataset_financial_baseline(anom["model_id"])
                    raw_val = float(anom["value"])
                    baseline_mrr = base_info["baseline_mrr"]
                    
                    # 100% Tautological Baseline Cap Policy: min(raw, baseline)
                    is_capped = raw_val > baseline_mrr
                    bounded_val = min(raw_val, baseline_mrr)
                    
                    cap_note = ""
                    if is_capped:
                        cap_note = (
                            f" [🛡️ Capped at 100% of dataset baseline (${baseline_mrr:,.0f} · {base_info['baseline_source']}) "
                            f"— raw projection (${raw_val:,.0f}) capped]"
                        )

                    cand = {
                        "candidate_id": f"cand_{str(anom['metric_id'])[:8]}_{str(ev_dict['event_id'])[:8]}",
                        "model_id": anom["model_id"],
                        "anomaly_metric": anom["metric_name"],
                        "anomaly_value": bounded_val,
                        "raw_anomaly_value": raw_val,
                        "baseline_mrr": baseline_mrr,
                        "baseline_source": base_info["baseline_source"],
                        "is_capped": is_capped,
                        "anomaly_date": recorded_dt.isoformat(),
                        "candidate_event_id": str(ev_dict["event_id"]),
                        "candidate_event_type": ev_dict["event_type"],
                        "candidate_node_type": ev_dict["node_type"],
                        "candidate_actor": ev_dict["actor"],
                        "event_date": event_dt.isoformat(),
                        "days_between": days_between,
                        "proposed_description": f"Metric '{anom['metric_name']}' anomaly (${bounded_val:,.0f}) observed {days_between} days after undocumented {ev_dict['node_type']} change by {ev_dict['actor']}.{cap_note}"
                    }
                    candidates.append(cand)

    # Upsert candidates into candidate_incidents table
    if candidates:
        upsert_cand_sql = """
            INSERT INTO candidate_incidents (
                candidate_id, model_id, anomaly_metric, anomaly_value, anomaly_date,
                candidate_event_id, days_between, proposed_description, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'unconfirmed')
            ON CONFLICT (candidate_id) DO NOTHING;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for c in candidates:
                    cur.execute(upsert_cand_sql, (
                        c["candidate_id"],
                        c["model_id"],
                        c["anomaly_metric"],
                        c["anomaly_value"],
                        c["anomaly_date"],
                        c["candidate_event_id"],
                        c["days_between"],
                        c["proposed_description"],
                    ))
            conn.commit()

    print(f"✅ Found {len(candidates)} candidate incident(s) from metric anomalies (lookback={lookback_days}d).")
    return candidates


def get_unconfirmed_candidate_incidents() -> List[Dict[str, Any]]:
    """
    D2.4 Returns all unconfirmed candidate incidents from the database.

    Read-only — does NOT trigger a discovery scan. Scanning is a write
    operation and should be triggered explicitly (background worker, test
    script, or POST /scan endpoint), not on every triage page load.
    This prevents duplicate candidates from accumulating on refresh.
    """
    query = """
        SELECT candidate_id, model_id, anomaly_metric, anomaly_value, anomaly_date,
               candidate_event_id, days_between, proposed_description, status, created_at
        FROM candidate_incidents
        WHERE status = 'unconfirmed'
        ORDER BY created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]

    unconfirmed = []
    for r in rows:
        unconfirmed.append({
            "candidate_id": r["candidate_id"],
            "model_id": r["model_id"],
            "anomaly_metric": r["anomaly_metric"],
            "anomaly_value": float(r["anomaly_value"]),
            "anomaly_date": r["anomaly_date"].isoformat() if r["anomaly_date"] else None,
            "candidate_event_id": str(r["candidate_event_id"]),
            "days_between": float(r["days_between"]),
            "proposed_description": r["proposed_description"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return unconfirmed



def confirm_candidate_incident(candidate_id: str) -> Dict[str, Any]:
    """
    D2.5 Confirm Candidate Incident:
    - Inserts a real row into incidents with root_cause_event_id = candidate_event_id.
    - Appends incident_confirmed to audit ledger.
    - Triggers populate_patterns() so organizational precedent updates immediately.
    """
    from services.ledger_service import append_to_ledger
    from services.correlation_service import populate_patterns

    # Fetch candidate
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM candidate_incidents WHERE candidate_id = %s;", (candidate_id,))
            cand = cur.fetchone()

    if not cand:
        raise ValueError(f"Candidate incident '{candidate_id}' not found.")

    cand = dict(cand)

    # Insert into incidents
    insert_inc_sql = """
        INSERT INTO incidents (
            model_id, detected_at, root_cause_event_id, description, fix_summary
        ) VALUES (%s, %s, %s, %s, 'Confirmed via Varve Candidate Incident Workflow')
        RETURNING incident_id;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(insert_inc_sql, (
                cand["model_id"],
                cand["anomaly_date"],
                cand["candidate_event_id"],
                cand["proposed_description"],
            ))
            inc_row = cur.fetchone()

            # Update candidate status
            cur.execute("UPDATE candidate_incidents SET status = 'confirmed' WHERE candidate_id = %s;", (candidate_id,))
        conn.commit()

    incident_id = str(inc_row["incident_id"])

    # Log to audit ledger
    append_to_ledger(
        event_type="incident_confirmed",
        finding_id=None,
        payload={
            "candidate_id": candidate_id,
            "incident_id": incident_id,
            "model_id": cand["model_id"],
            "root_cause_event_id": str(cand["candidate_event_id"]),
            "anomaly_metric": cand["anomaly_metric"],
            "anomaly_value": float(cand["anomaly_value"]),
            "proposed_description": cand["proposed_description"],
        }
    )

    # Trigger patterns rollup update to reflect new evidence immediately!
    populate_patterns()

    print(f"✅ Candidate '{candidate_id}' confirmed -> Created incident '{incident_id}' & updated org pattern rollups.")
    return {
        "status": "confirmed",
        "candidate_id": candidate_id,
        "incident_id": incident_id,
        "message": "Incident confirmed! Real incident row created and organizational precedent updated immediately."
    }


def dismiss_candidate_incident(candidate_id: str) -> Dict[str, Any]:
    """
    D2.5 Dismiss Candidate Incident:
    - Updates candidate status to 'dismissed'.
    - Appends incident_dismissed to audit ledger (free negative evidence!).
    - Does NOT touch incidents table.
    """
    from services.ledger_service import append_to_ledger

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM candidate_incidents WHERE candidate_id = %s;", (candidate_id,))
            cand = cur.fetchone()

    if not cand:
        raise ValueError(f"Candidate incident '{candidate_id}' not found.")

    cand = dict(cand)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE candidate_incidents SET status = 'dismissed' WHERE candidate_id = %s;", (candidate_id,))
        conn.commit()

    # Log to audit ledger as free negative evidence
    append_to_ledger(
        event_type="incident_dismissed",
        finding_id=None,
        payload={
            "candidate_id": candidate_id,
            "model_id": cand["model_id"],
            "root_cause_event_id": str(cand["candidate_event_id"]),
            "anomaly_metric": cand["anomaly_metric"],
            "anomaly_value": float(cand["anomaly_value"]),
            "proposed_description": cand["proposed_description"],
            "reason": "Dismissed by operator (logged as negative evidence)."
        }
    )

    print(f"✅ Candidate '{candidate_id}' dismissed -> Logged negative evidence in audit ledger.")
    return {
        "status": "dismissed",
        "candidate_id": candidate_id,
        "message": "Candidate dismissed. Logged in audit ledger as negative evidence."
    }
