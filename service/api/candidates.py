"""
FastAPI Router for Candidate Incidents (Phase D2.4 - D2.5)
"""

import sys
import os
from fastapi import APIRouter, HTTPException

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.anomaly_service import (
    get_unconfirmed_candidate_incidents,
    confirm_candidate_incident,
    dismiss_candidate_incident,
)

router = APIRouter(prefix="/candidate-incidents", tags=["candidate-incidents"])


@router.get("")
def list_candidate_incidents():
    """
    D2.4 Returns all unconfirmed candidate incidents for human triage review.
    """
    try:
        candidates = get_unconfirmed_candidate_incidents()
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch candidate incidents: {str(e)}")


@router.post("/{candidate_id}/confirm")
def confirm_candidate(candidate_id: str):
    """
    D2.5 Confirm Candidate Incident:
    Inserts a real row into incidents, logs incident_confirmed in audit ledger,
    and updates patterns rollups immediately.
    """
    try:
        res = confirm_candidate_incident(candidate_id)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm candidate incident: {str(e)}")


@router.post("/{candidate_id}/dismiss")
def dismiss_candidate(candidate_id: str):
    """
    D2.5 Dismiss Candidate Incident:
    Marks candidate as dismissed and logs incident_dismissed in audit ledger
    as free negative evidence. Does not touch incidents table.
    """
    try:
        res = dismiss_candidate_incident(candidate_id)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss candidate incident: {str(e)}")
