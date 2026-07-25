"""
Varve Ledger Service — Phase B (Audit Ledger)

Core capability:
- append_to_ledger(event_type, finding_id, payload): Appends a cryptographic hash-chained decision entry to PostgreSQL.
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection


def append_to_ledger(
    event_type: str,
    finding_id: Optional[str],
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Appends a new decision entry to the ledger table.

    - Fetches the this_hash of the most recent row in ledger (or None if empty).
    - Computes this_hash = sha256(str(prev_hash) + event_type + str(finding_id) + json.dumps(payload, sort_keys=True) + str(now))
    - Inserts the new row with both hashes and returns the created record.
    """
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Fetch this_hash of most recent row
            cur.execute("""
                SELECT this_hash
                FROM ledger
                ORDER BY created_at DESC, ledger_id DESC
                LIMIT 1;
            """)
            last_row = cur.fetchone()
            prev_hash = last_row["this_hash"] if last_row else None

            # 2. Compute hash
            payload_str = json.dumps(payload, sort_keys=True)
            data_to_hash = f"{str(prev_hash)}{event_type}{str(finding_id)}{payload_str}{str(now)}"
            this_hash = hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

            # 3. Insert row
            insert_query = """
                INSERT INTO ledger (event_type, finding_id, payload, prev_hash, this_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING ledger_id, event_type, finding_id, payload, prev_hash, this_hash, created_at;
            """
            cur.execute(
                insert_query,
                (event_type, finding_id, json.dumps(payload), prev_hash, this_hash, now)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)


def verify_ledger_chain() -> Dict[str, Any]:
    """
    B3.1 Verification function:
    - Fetches all ledger rows ordered by created_at ascending.
    - Recomputes SHA-256 for each row and verifies hash linkage against prev_hash.
    - Returns verification summary dictionary.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ledger_id, event_type, finding_id, payload, prev_hash, this_hash, created_at
                FROM ledger
                ORDER BY created_at ASC, ledger_id ASC;
            """)
            rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return {
            "valid": True,
            "total_verified": 0,
            "message": "Ledger is empty. Zero entries to verify."
        }

    expected_prev_hash = None
    results = []

    for idx, r in enumerate(rows, 1):
        prev_h = r["prev_hash"]
        this_h = r["this_hash"]
        e_type = r["event_type"]
        f_id = r["finding_id"]
        payload_obj = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"])
        payload_str = json.dumps(payload_obj, sort_keys=True)
        ts = r["created_at"]

        # Check 1: prev_hash linkage check
        if prev_h != expected_prev_hash:
            err_msg = (
                f"Chain linkage broken at Row {idx} (ledger_id={r['ledger_id']}): "
                f"expected prev_hash '{expected_prev_hash}', got '{prev_h}'."
            )
            return {
                "valid": False,
                "total_verified": idx - 1,
                "failed_row_index": idx,
                "failed_ledger_id": str(r["ledger_id"]),
                "error": err_msg,
            }

        # Check 2: recompute hash
        data_to_hash = f"{str(prev_h)}{e_type}{str(f_id)}{payload_str}{str(ts)}"
        recomputed_hash = hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

        if recomputed_hash != this_h:
            err_msg = (
                f"Content tampering detected at Row {idx} (ledger_id={r['ledger_id']}): "
                f"stored hash '{this_h}', recomputed '{recomputed_hash}'."
            )
            return {
                "valid": False,
                "total_verified": idx - 1,
                "failed_row_index": idx,
                "failed_ledger_id": str(r["ledger_id"]),
                "error": err_msg,
            }

        expected_prev_hash = this_h
        results.append({
            "index": idx,
            "ledger_id": str(r["ledger_id"]),
            "event_type": e_type,
            "finding_id": str(f_id) if f_id else None,
            "this_hash": this_h,
            "status": "PASS",
        })

    return {
        "valid": True,
        "total_verified": len(rows),
        "details": results,
        "message": f"✔ {len(rows)}/{len(rows)} ledger entries verified, chain intact.",
    }
