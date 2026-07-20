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