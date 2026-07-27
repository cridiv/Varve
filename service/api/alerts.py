"""
Varve Alert Router — /findings/{finding_id}/alert

Exposes a single endpoint that:
  1. Reads the finding from the DB (same shape as GET /findings/{finding_id})
  2. Calls slack_service.send_finding_alert()
  3. Returns the delivery result

No SDK dependency — the Slack send is a plain urllib HTTP POST.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import sys, os
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

import psycopg2
from config.config import POSTGRES_DSN
from services.slack_service import send_finding_alert

alerts_router = APIRouter(tags=["alerts"])


class AlertRequest(BaseModel):
    slack_channel: Optional[str] = "#data-incidents"  # override channel if using Bot token path


@alerts_router.post("/findings/{finding_id}/alert")
def alert_finding(finding_id: str, body: AlertRequest = AlertRequest()):
    """
    POST /findings/{finding_id}/alert

    Looks up the finding and dispatches a formatted Slack Block Kit message
    to SLACK_WEBHOOK_URL (or SLACK_BOT_TOKEN + body.slack_channel).

    Returns:
        { "ok": bool, "status": int|null, "error": str|null }
    """
    conn = None
    try:
        conn = psycopg2.connect(POSTGRES_DSN)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                f.finding_id,
                f.model_id      AS model_name,
                f.severity,
                f.narrative,
                f.recommended_action,
                f.evidence_scope,
                f.routed_to_team,
                ROUND(
                    EXTRACT(EPOCH FROM (
                        COALESCE(i.incident_date, NOW()) - f.event_timestamp
                    )) / 86400
                )::INT           AS detection_lag_days
            FROM findings f
            LEFT JOIN incidents i ON i.root_cause_event_id = f.event_id::TEXT
            WHERE f.finding_id = %s
            LIMIT 1
            """,
            (finding_id,),
        )
        row = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        if conn:
            conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

    cols = [
        "finding_id", "model_name", "severity", "narrative",
        "recommended_action", "evidence_scope", "routed_to_team", "detection_lag_days"
    ]
    finding = dict(zip(cols, row))
    finding["slack_channel"] = body.slack_channel

    result = send_finding_alert(finding)
    if not result["ok"]:
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "Slack delivery failed",
        )
    return result
