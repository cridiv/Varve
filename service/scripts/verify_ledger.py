#!/usr/bin/env python3
"""
Varve CLI — Ledger Chain Verification Tool (Phase B)

Usage:
  python scripts/verify_ledger.py

Fetches all entries from the PostgreSQL audit ledger table, recomputes
the SHA-256 hash for every row in sequential order, and verifies that
both the content and hash chain linkage are 100% intact.
"""

import sys
import os
import json
import hashlib

# Ensure service root directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(script_dir)
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection


def main():
    print("\n=======================================================")
    print("      VARVE AUDIT LEDGER — HASH CHAIN VERIFIER         ")
    print("=======================================================\n")

    query = """
        SELECT ledger_id, event_type, finding_id, payload, prev_hash, this_hash, created_at
        FROM ledger
        ORDER BY created_at ASC, ledger_id ASC;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"❌ Database error fetching ledger rows: {e}")
        sys.exit(1)

    total_rows = len(rows)

    if total_rows == 0:
        print("⚠️ Ledger table is empty. 0 entries to verify.")
        sys.exit(0)

    print(f"Verifying {total_rows} ledger entries sequentially...\n")

    expected_prev_hash = None
    failed_row = None

    for idx, r in enumerate(rows, 1):
        ledger_id = str(r["ledger_id"])
        event_type = r["event_type"]
        finding_id = str(r["finding_id"]) if r["finding_id"] else "None"
        prev_hash = r["prev_hash"]
        this_hash = r["this_hash"]
        created_at = r["created_at"]

        # Parse payload
        payload_obj = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"])
        payload_str = json.dumps(payload_obj, sort_keys=True)

        # Check 1: Previous hash linkage
        if prev_hash != expected_prev_hash:
            print(f"✖ [FAIL] Row {idx:02d} | ID: {ledger_id[:8]}... | Event: {event_type:<15}")
            print(f"  └─ 🚨 LINK BREAKAGE DETECTED!")
            print(f"     Expected prev_hash: {expected_prev_hash}")
            print(f"     Found prev_hash:    {prev_hash}")
            failed_row = idx
            break

        # Check 2: Content hash recomputation
        data_to_hash = f"{str(prev_hash)}{event_type}{str(r['finding_id'])}{payload_str}{str(created_at)}"
        recomputed_hash = hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

        if recomputed_hash != this_hash:
            print(f"✖ [FAIL] Row {idx:02d} | ID: {ledger_id[:8]}... | Event: {event_type:<15}")
            print(f"  └─ 🚨 CONTENT TAMPERING DETECTED!")
            print(f"     Stored hash:     {this_hash}")
            print(f"     Recomputed hash: {recomputed_hash}")
            failed_row = idx
            break

        # Success for this row
        prev_display = prev_hash[:12] + "..." if prev_hash else "None"
        this_display = this_hash[:12] + "..."
        print(f"✔ [PASS] Row {idx:02d} | Event: {event_type:<18} | Finding: {finding_id[:8]}... | this_hash: {this_display} | prev_hash: {prev_display}")

        expected_prev_hash = this_hash

    print("\n-------------------------------------------------------")
    if failed_row is not None:
        print(f"✖ VERIFICATION FAILED at row {failed_row}/{total_rows}.")
        print("  Chain linkage or payload content has been altered!")
        sys.exit(1)
    else:
        print(f"✔ {total_rows}/{total_rows} ledger entries verified, chain intact.")
        print("  Zero tampering detected. All decision records are mathematically authentic.")
        sys.exit(0)


if __name__ == "__main__":
    main()
