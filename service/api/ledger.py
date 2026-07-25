"""
FastAPI Router for Audit Ledger Verification & Entries — Phase B
"""

import sys
import os
from fastapi import APIRouter, HTTPException

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.ledger_service import verify_ledger_chain

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/verify")
def get_ledger_verification():
    """
    B4.1 Endpoint: Runs hash chain verification across all ledger entries.
    Returns JSON:
      { "verified": true, "entries_checked": N }
    or failure detail if chain tampering is detected.
    """
    try:
        res = verify_ledger_chain()
        if res.get("valid"):
            return {
                "verified": True,
                "entries_checked": res.get("total_verified", 0),
                "message": res.get("message", "Ledger chain intact."),
            }
        else:
            return {
                "verified": False,
                "entries_checked": res.get("total_verified", 0),
                "failed_row_index": res.get("failed_row_index"),
                "failed_ledger_id": res.get("failed_ledger_id"),
                "error": res.get("error"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ledger verification error: {str(e)}")
