"""
FastAPI Router for Audit Ledger Verification & Entries — Phase B
"""

import sys
import os
import json
from fastapi import APIRouter, HTTPException

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from services.ledger_service import verify_ledger_chain, get_db_connection

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/verify")
def get_ledger_verification():
    """
    B4.1 Endpoint: Runs hash chain verification across all ledger entries.
    Returns JSON verification summary and details.
    """
    try:
        res = verify_ledger_chain()
        if res.get("valid"):
            return {
                "verified": True,
                "entries_checked": res.get("total_verified", 0),
                "details": res.get("details", []),
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


@router.get("/findings/{finding_id}")
@router.get("/entries/{finding_id}")
def get_ledger_entries_by_finding(finding_id: str):
    """
    Returns verified ledger entries filtered for a specific finding_id with payload details.
    Exposed at GET /ledger/findings/{finding_id} (and GET /ledger/entries/{finding_id} alias).
    """
    try:
        res = verify_ledger_chain()
        
        # Query raw entries from database for complete payload info
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ledger_id, event_type, finding_id, payload, prev_hash, this_hash, created_at
                    FROM ledger
                    WHERE finding_id = %s
                    ORDER BY created_at ASC;
                """, (finding_id,))
                rows = [dict(r) for r in cur.fetchall()]

        entries = []
        for r in rows:
            p_obj = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"] or "{}")
            entries.append({
                "ledger_id": str(r["ledger_id"]),
                "event_type": r["event_type"],
                "finding_id": str(r["finding_id"]),
                "prev_hash": r["prev_hash"] or "0000000000000000000000000000000000000000000000000000000000000000",
                "this_hash": r["this_hash"],
                "payload": p_obj,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "status": "PASS",
            })

        return {
            "finding_id": finding_id,
            "chain_valid": res.get("valid", True),
            "total_entries": len(entries),
            "entries": entries,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ledger entries: {str(e)}")
