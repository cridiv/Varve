"""
FastAPI router for actor identity resolution and pattern cross-model analytics.
"""

from fastapi import APIRouter, HTTPException
from db.connection import get_db_connection
from services.correlation_service import get_all_actor_events
from services.actor_resolution_service import (
    resolve_and_store_actor,
    resolve_all_lineage_actors,
    get_all_actor_mappings,
    match_actor_to_datahub_owner,
)

router = APIRouter(tags=["patterns"])


@router.post("/actors/resolve")
def run_actor_resolution_step():
    """
    Resolution Step: Scans lineage events, resolves actor names against
    known DataHub owners, and stores the matches in actor_owner_mappings table.
    """
    try:
        mappings = resolve_all_lineage_actors()
        return {
            "status": "success",
            "message": f"Successfully resolved and stored {len(mappings)} actor-to-owner identity mappings.",
            "total_mappings": len(mappings),
            "mappings": mappings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Actor identity resolution failed: {str(e)}")


@router.get("/actors/mappings")
def get_actor_identity_mappings():
    """
    Returns stored actor-to-owner identity mappings from database.
    """
    try:
        mappings = get_all_actor_mappings()
        return {
            "total": len(mappings),
            "mappings": mappings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch actor mappings: {str(e)}")


@router.get("/patterns/by-actor/{actor}")
def get_patterns_by_actor(actor: str):
    """
    Returns every lineage event + any linked incident for an actor across ALL models.
    Includes identity resolution to match lineage free-text names with DataHub owners.
    """
    # 1. Run identity resolution step for requested actor & store match
    resolved_identity = resolve_and_store_actor(actor)

    rows = get_all_actor_events(actor)

    # 2. If no direct lineage event authoring rows found, check routed findings (e.g. DataHub Owner)
    if not rows:
        find_query = """
            SELECT 
                f.finding_id,
                f.model_id,
                f.severity,
                f.routed_to_team,
                f.narrative,
                f.created_at,
                f.related_event_id,
                e.node_type,
                e.event_type,
                e.event_timestamp,
                e.actor,
                e.actor_departed_within_90d,
                e.documentation_present,
                i.incident_id,
                i.model_id AS incident_model_id,
                i.detected_at,
                i.description,
                i.fix_summary,
                EXTRACT(EPOCH FROM (i.detected_at - e.event_timestamp)) / 86400.0 AS detection_lag_days
            FROM findings f
            JOIN lineage_events e ON f.related_event_id = e.event_id
            LEFT JOIN incidents i ON i.root_cause_event_id = e.event_id
            WHERE LOWER(f.routed_to_team) LIKE LOWER(%s)
               OR LOWER(f.routed_to_team) LIKE LOWER(%s)
            ORDER BY f.created_at DESC;
        """
        search_term = f"%{actor}%"
        disp_term = f"%{resolved_identity['datahub_display_name'].split('(')[0].strip()}%"
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(find_query, (search_term, disp_term))
                rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        raise HTTPException(status_code=404, detail=f"No lineage events or owned datasets found for actor '{actor}'")

    seen_event_ids = set()
    events_out = []
    for r in rows:
        eid = str(r["event_id"])
        if eid in seen_event_ids:
            continue
        seen_event_ids.add(eid)

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
                "detection_lag_days": int(round(float(r["detection_lag_days"]))) if r.get("detection_lag_days") is not None else None,
            }

        events_out.append({
            "event_id": eid,
            "model_id": r["model_id"],
            "model_name": model_name,
            "node_type": r.get("node_type", "dataset"),
            "event_type": r.get("event_type", "owned_dataset_finding"),
            "event_timestamp": r["event_timestamp"].isoformat() if r.get("event_timestamp") else r.get("created_at").isoformat() if r.get("created_at") else None,
            "actor_departed_within_90d": bool(r.get("actor_departed_within_90d", False)),
            "documentation_present": bool(r.get("documentation_present", True)),
            "linked_incident": incident_out,
        })

    pattern_query = """
        SELECT pattern_type, times_observed, times_preceded_incident, avg_detection_lag_days
        FROM patterns
        WHERE scope_key = %s OR scope_key = %s OR scope_key = 'org_wide'
        ORDER BY times_preceded_incident DESC
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(pattern_query, (actor, resolved_identity.get("datahub_display_name")))
            pattern_row = cur.fetchone()

    pattern_summary = None
    if pattern_row:
        pr = dict(pattern_row)
        pattern_summary = {
            "pattern_type": pr["pattern_type"],
            "times_observed": pr["times_observed"],
            "times_preceded_incident": pr["times_preceded_incident"],
            "incident_rate_pct": round(
                100 * pr["times_preceded_incident"] / pr["times_observed"]
            ) if pr["times_observed"] else 0,
            "avg_detection_lag_days": int(round(float(pr["avg_detection_lag_days"] or 0))),
        }

    return {
        "actor": actor,
        "identity_mapping": resolved_identity,
        "total_events": len(events_out),
        "events_with_incidents": sum(1 for e in events_out if e["linked_incident"]),
        "pattern_summary": pattern_summary,
        "events": events_out,
    }
