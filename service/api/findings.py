"""
FastAPI router for findings endpoints (risk-ranking, detail view, writeback).
"""

from fastapi import APIRouter, HTTPException
from db.connection import get_db_connection
from services.datahub_service import writeback_finding_to_datahub, confirm_datahub_annotation

router = APIRouter(tags=["findings"])


EVIDENCE_LABELS = {
    "model": "Backed by direct model incident history",
    "actor": "Backed by actor cross-model incident history",
    "org_wide": "Backed by company-wide pattern history",
    "industry_general": "Backed by published industry data (Cold-start fallback)",
}

TAG_SOURCE_LABELS = {
    "datahub_native": "Verified DataHub Catalog Tag",
    "inferred": "Inferred from Schema (Heuristic Fallback)",
    "none": "Untagged",
}


@router.get("/models/risk-ranking")
def get_risk_ranking():
    """
    Returns all findings ordered by severity (high first) and validation status.
    Joins findings with lineage_events to return clean summary for triage dashboard.
    """
    query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.evidence_scope,
            f.routed_to_team,
            f.severity_multiplier,
            f.tag_source,
            f.status,
            f.narrative,
            f.recommended_action,
            f.written_back_at,
            f.created_at,
            e.actor,
            e.node_type,
            e.event_timestamp,
            i.detected_at AS incident_detected_at
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        LEFT JOIN incidents i ON f.related_event_id = i.root_cause_event_id
        ORDER BY 
            CASE WHEN f.severity = 'high' THEN 1 ELSE 2 END,
            f.validated DESC,
            f.created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]

    rankings = []
    for r in rows:
        urn_parts = r["model_id"].split(".")
        display_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]
        ev_scope = r.get("evidence_scope", "org_wide")
        ts = r.get("tag_source", "none")
        
        event_ts = r.get("event_timestamp")
        inc_ts = r.get("incident_detected_at")
        lag_days = int(round((inc_ts - event_ts).total_seconds() / 86400.0)) if (inc_ts and event_ts) else None
        
        rankings.append({
            "finding_id": str(r["finding_id"]),
            "model_id": r["model_id"],
            "model_name": display_name,
            "severity": r["severity"],
            "validated": r["validated"],
            "evidence_scope": ev_scope,
            "evidence_label": EVIDENCE_LABELS.get(ev_scope, "Backed by company-wide pattern history"),
            "routed_to_team": r.get("routed_to_team", "Ian Chen (Director of Data Engineering)"),
            "severity_multiplier": float(r.get("severity_multiplier") or 1.0),
            "tag_source": ts,
            "tag_source_label": TAG_SOURCE_LABELS.get(ts, "Untagged"),
            "status": r["status"],
            "actor": r["actor"],
            "node_type": r["node_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r["event_timestamp"] else None,
            "detection_lag_days": lag_days,
            "summary": r["narrative"],
            "recommended_action": r["recommended_action"],
            "written_back": r["written_back_at"] is not None,
        })

    return rankings


@router.get("/findings/by-team/{team}")
def get_findings_by_team(team: str):
    """
    E1.3 Returns all findings routed to a specific team or owner name.
    Supports case-insensitive partial matching (e.g. 'jonny1', 'patrick1', 'Ian Chen').
    """
    query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.evidence_scope,
            f.routed_to_team,
            f.severity_multiplier,
            f.tag_source,
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
        WHERE LOWER(f.routed_to_team) LIKE LOWER(%s)
        ORDER BY 
            CASE WHEN f.severity = 'high' THEN 1 ELSE 2 END,
            f.validated DESC,
            f.created_at DESC;
    """
    search_term = f"%{team}%"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (search_term,))
            rows = [dict(r) for r in cur.fetchall()]

    team_findings = []
    for r in rows:
        urn_parts = r["model_id"].split(".")
        display_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]
        ev_scope = r.get("evidence_scope", "org_wide")
        ts = r.get("tag_source", "none")

        team_findings.append({
            "finding_id": str(r["finding_id"]),
            "model_id": r["model_id"],
            "model_name": display_name,
            "severity": r["severity"],
            "validated": r["validated"],
            "evidence_scope": ev_scope,
            "evidence_label": EVIDENCE_LABELS.get(ev_scope, "Backed by company-wide pattern history"),
            "routed_to_team": r.get("routed_to_team", "Ian Chen (Director of Data Engineering)"),
            "severity_multiplier": float(r.get("severity_multiplier") or 1.0),
            "tag_source": ts,
            "tag_source_label": TAG_SOURCE_LABELS.get(ts, "Untagged"),
            "status": r["status"],
            "actor": r["actor"],
            "node_type": r["node_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r["event_timestamp"] else None,
            "summary": r["narrative"],
            "recommended_action": r["recommended_action"],
            "written_back": r["written_back_at"] is not None,
        })

    return team_findings


@router.get("/findings/{finding_id}")
def get_finding_detail(finding_id: str):
    """
    Returns full details for one finding including related lineage event
    and matched root-cause incident.
    """
    finding_query = """
        SELECT 
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.evidence_scope,
            f.routed_to_team,
            f.severity_multiplier,
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
        event_ts = finding["event_timestamp"]
        detected_ts = inc["detected_at"]
        detection_lag = None
        if detected_ts and event_ts:
            detection_lag = int(round((detected_ts - event_ts).total_seconds() / 86400.0))

        is_cross = inc["target_model_id"] != finding["model_id"]

        matched_incident = {
            "incident_id": str(inc["incident_id"]),
            "target_model_id": inc["target_model_id"],
            "detected_at": inc["detected_at"].isoformat() if inc["detected_at"] else None,
            "resolved_at": inc["resolved_at"].isoformat() if inc["resolved_at"] else None,
            "description": inc["description"],
            "fix_summary": inc["fix_summary"],
            "detection_lag_days": detection_lag,
            "is_cross_model": is_cross,
        }

    urn_parts = finding["model_id"].split(".")
    display_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else finding["model_id"]
    ev_scope = finding.get("evidence_scope", "org_wide")
    ts = finding.get("tag_source", "none")

    return {
        "finding_id": str(finding["finding_id"]),
        "model_id": finding["model_id"],
        "model_name": display_name,
        "severity": finding["severity"],
        "validated": finding["validated"],
        "evidence_scope": ev_scope,
        "evidence_label": EVIDENCE_LABELS.get(ev_scope, "Backed by company-wide pattern history"),
        "routed_to_team": finding.get("routed_to_team", "Ian Chen (Director of Data Engineering)"),
        "severity_multiplier": float(finding.get("severity_multiplier") or 1.0),
        "tag_source": ts,
        "tag_source_label": TAG_SOURCE_LABELS.get(ts, "Untagged"),
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


@router.post("/findings/{finding_id}/writeback")
def trigger_writeback(finding_id: str, force: bool = False):
    """
    Triggers DataHub metadata write-back for the specified finding.
    Annotates the lineage dataset node on DataHub GMS and updates database.
    Idempotent by default: skips duplicate emissions and ledger appends if already written back.
    """
    try:
        res = writeback_finding_to_datahub(finding_id, force=force)
        confirm_datahub_annotation(res["dataset_urn"])
        msg = (
            "Finding metadata already written back to DataHub (idempotent skip)"
            if res.get("already_written_back")
            else "Finding metadata successfully written back to DataHub"
        )
        return {
            "status": "success",
            "message": msg,
            "details": res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DataHub write-back failed: {str(e)}")
