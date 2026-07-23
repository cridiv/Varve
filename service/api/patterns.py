"""
FastAPI router for actor and pattern cross-model analytics.
"""

from fastapi import APIRouter, HTTPException
from db.connection import get_db_connection
from services.correlation_service import get_all_actor_events

router = APIRouter(tags=["patterns"])


@router.get("/patterns/by-actor/{actor}")
def get_patterns_by_actor(actor: str):
    """
    Returns every lineage event + any linked incident for an actor,
    across ALL models. This is the cross-model history screen.
    """
    rows = get_all_actor_events(actor)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No events found for actor '{actor}'")

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
