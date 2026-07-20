"""
Varve FastAPI Application — Main Entry Point

Exposes minimum viable REST endpoints for Tier 1:
- GET /health
- GET /models/risk-ranking
- GET /findings/{finding_id}
"""

import sys
import os
from typing import List, Dict, Any

# Ensure service directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

from config.config import (
    MODEL_NAME,
    DATAHUB_GMS_URL,
    POSTGRES_DSN,
    validate_config,
)

app = FastAPI(title="Varve AI API", version="0.1.0")

# Enable CORS for React frontend (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    return psycopg2.connect(POSTGRES_DSN, cursor_factory=RealDictCursor)


@app.on_event("startup")
def on_startup():
    try:
        validate_config()
    except Exception as e:
        print(f"[warning] Config validation warning: {e}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_name": MODEL_NAME,
        "datahub_gms_url": DATAHUB_GMS_URL,
    }


@app.get("/models/risk-ranking")
def get_risk_ranking():
    """
    Step 7.1: Returns all findings ordered by severity (high first) and validation status.
    Joins findings with lineage_events to return clean summary for triage dashboard.
    """
    query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.status,
            f.narrative,
            f.recommended_action,
            f.written_back_at,
            f.created_at,
            e.actor,
            e.node_type,
            e.event_timestamp
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        ORDER BY 
            CASE WHEN f.severity = 'high' THEN 1 ELSE 2 END,
            f.validated DESC,
            f.created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]

    # Format JSON response
    rankings = []
    for r in rows:
        # Extract friendly dataset basename
        urn_parts = r["model_id"].split(".")
        display_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]
        
        rankings.append({
            "finding_id": str(r["finding_id"]),
            "model_id": r["model_id"],
            "model_name": display_name,
            "severity": r["severity"],
            "validated": r["validated"],
            "status": r["status"],
            "actor": r["actor"],
            "node_type": r["node_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r["event_timestamp"] else None,
            "summary": r["narrative"],
            "recommended_action": r["recommended_action"],
            "written_back": r["written_back_at"] is not None,
        })

    return rankings


@app.get("/findings/{finding_id}")
def get_finding_detail(finding_id: str):
    """
    Step 7.2: Returns full details for one finding including related lineage event
    and matched root-cause incident.
    """
    finding_query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.narrative,
            f.recommended_action,
            f.status,
            f.written_back_at,
            f.created_at,
            f.related_event_id,
            e.node_type,
            e.node_urn,
            e.event_type,
            e.event_timestamp,
            e.actor,
            e.documentation_present
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        WHERE f.finding_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(finding_query, (finding_id,))
            finding = cur.fetchone()

    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")

    finding = dict(finding)

    # Fetch matched incident if any
    incident_query = """
        SELECT 
            incident_id,
            model_id AS target_model_id,
            detected_at,
            resolved_at,
            description,
            fix_summary
        FROM incidents
        WHERE root_cause_event_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(incident_query, (finding["related_event_id"],))
            incidents = [dict(r) for r in cur.fetchall()]

    matched_incident = None
    if incidents:
        inc = incidents[0]
        matched_incident = {
            "incident_id": str(inc["incident_id"]),
            "target_model_id": inc["target_model_id"],
            "detected_at": inc["detected_at"].isoformat() if inc["detected_at"] else None,
            "resolved_at": inc["resolved_at"].isoformat() if inc["resolved_at"] else None,
            "description": inc["description"],
            "fix_summary": inc["fix_summary"],
        }

    # Format response
    urn_parts = finding["model_id"].split(".")
    display_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else finding["model_id"]

    return {
        "finding_id": str(finding["finding_id"]),
        "model_id": finding["model_id"],
        "model_name": display_name,
        "severity": finding["severity"],
        "validated": finding["validated"],
        "status": finding["status"],
        "narrative": finding["narrative"],
        "recommended_action": finding["recommended_action"],
        "written_back": finding["written_back_at"] is not None,
        "written_back_at": finding["written_back_at"].isoformat() if finding["written_back_at"] else None,
        "created_at": finding["created_at"].isoformat() if finding["created_at"] else None,
        "event_details": {
            "event_id": str(finding["related_event_id"]),
            "node_type": finding["node_type"],
            "node_urn": finding["node_urn"],
            "event_type": finding["event_type"],
            "event_timestamp": finding["event_timestamp"].isoformat() if finding["event_timestamp"] else None,
            "actor": finding["actor"],
            "documentation_present": finding["documentation_present"],
        },
        "matched_incident": matched_incident,
    }


@app.post("/findings/{finding_id}/writeback")
def trigger_writeback(finding_id: str):
    """
    Step 9.3: Triggers DataHub metadata write-back for the specified finding.
    Annotates the lineage dataset node on DataHub GMS and updates database.
    """
    from datahub_writeback import writeback_finding_to_datahub, confirm_datahub_annotation
    try:
        res = writeback_finding_to_datahub(finding_id)
        confirm_datahub_annotation(res["dataset_urn"])
        return {
            "status": "success",
            "message": "Finding metadata successfully written back to DataHub",
            "details": res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DataHub write-back failed: {str(e)}")


@app.get("/patterns/by-actor/{actor}")
def get_patterns_by_actor(actor: str):
    """
    Step 14.1: Returns every lineage event + any linked incident for an actor,
    across ALL models. This is the cross-model history screen.
    """
    from correlation import get_all_actor_events

    rows = get_all_actor_events(actor)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No events found for actor '{actor}'")

    # Group events; attach incident if present
    events_out = []
    for r in rows:
        urn_parts = r["model_id"].split(".")
        model_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]

        incident_out = None
        if r.get("incident_id"):
            inc_urn = r.get("incident_model_id", "")
            inc_model_name = inc_urn.split(".")[-1].replace(",PROD)", "") if inc_urn else inc_urn
            incident_out = {
                "incident_id": str(r["incident_id"]),
                "incident_model_id": inc_urn,
                "incident_model_name": inc_model_name,
                "detected_at": r["detected_at"].isoformat() if r.get("detected_at") else None,
                "description": r.get("description"),
                "fix_summary": r.get("fix_summary"),
                "detection_lag_days": round(float(r["detection_lag_days"]), 1) if r.get("detection_lag_days") else None,
            }

        events_out.append({
            "event_id": str(r["event_id"]),
            "model_id": r["model_id"],
            "model_name": model_name,
            "node_type": r["node_type"],
            "event_type": r["event_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r.get("event_timestamp") else None,
            "actor_departed_within_90d": bool(r.get("actor_departed_within_90d")),
            "documentation_present": bool(r.get("documentation_present")),
            "linked_incident": incident_out,
        })

    # Fetch actor-scoped pattern row if present
    pattern_query = """
        SELECT pattern_type, times_observed, times_preceded_incident, avg_detection_lag_days
        FROM patterns
        WHERE scope_key = %s
        ORDER BY times_preceded_incident DESC
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(pattern_query, (actor,))
            pattern_row = cur.fetchone()

    pattern_summary = None
    if pattern_row:
        pr = dict(pattern_row)
        pattern_summary = {
            "pattern_type": pr["pattern_type"],
            "times_observed": pr["times_observed"],
            "times_preceded_incident": pr["times_preceded_incident"],
            "incident_rate_pct": round(
                100 * pr["times_preceded_incident"] / pr["times_observed"], 1
            ) if pr["times_observed"] else 0,
            "avg_detection_lag_days": float(pr["avg_detection_lag_days"] or 0),
        }

    return {
        "actor": actor,
        "total_events": len(events_out),
        "events_with_incidents": sum(1 for e in events_out if e["linked_incident"]),
        "pattern_summary": pattern_summary,
        "events": events_out,
    }