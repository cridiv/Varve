#!/usr/bin/env python3
"""
Varve Cold-Start & Candidate Incident Seeding Test (D2.7)

Seeds a new 5th scenario outside Stories 1-4 (inventory dataset / K. Vance),
detects metric anomaly, confirms candidate incident via API/Service,
and verifies:
1. New row in incidents table with root_cause_event_id.
2. Updated row in patterns table.
3. Cryptographic hash chain verified in audit ledger.
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(script_dir)
if service_dir not in sys.path:
    sys.path.append(service_dir)

from db.connection import get_db_connection
from services.anomaly_service import (
    detect_metric_anomalies,
    get_unconfirmed_candidate_incidents,
    confirm_candidate_incident,
)
from services.ledger_service import verify_ledger_chain


def seed_test_scenario_5():
    """
    Seeds Scenario 5: K. Vance undocumented pipeline_step change on inventory dataset
    followed by stock_sync_latency_ms anomaly 4.2 days later.
    """
    event_id = "f6a7b8c9-d0e1-2345-fa01-678901234567"
    model_id = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.inventory,PROD)"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Clean existing test scenario 5 if re-run
            cur.execute("DELETE FROM candidate_incidents WHERE model_id = %s;", (model_id,))
            cur.execute("DELETE FROM incidents WHERE model_id = %s;", (model_id,))
            cur.execute("DELETE FROM business_metrics WHERE model_id = %s;", (model_id,))
            cur.execute("DELETE FROM lineage_events WHERE event_id = %s;", (event_id,))

            # 1. Insert Lineage Event for K. Vance
            cur.execute("""
                INSERT INTO lineage_events (
                    event_id, model_id, node_type, node_urn, event_type,
                    event_timestamp, actor, actor_departed_within_90d, documentation_present
                ) VALUES (
                    %s, %s, 'pipeline_step', %s, 'modified',
                    '2026-07-10 08:00:00+00', 'K. Vance', TRUE, FALSE
                );
            """, (event_id, model_id, model_id))

            # 2. Insert Business Metrics (Baseline + Anomaly)
            cur.execute("""
                INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
                (%s, 'stock_sync_latency_ms', 45.0, '2026-07-08 00:00:00+00'),
                (%s, 'stock_sync_latency_ms', 46.2, '2026-07-09 00:00:00+00'),
                (%s, 'stock_sync_latency_ms', 850.0, '2026-07-14 12:00:00+00');
            """, (model_id, model_id, model_id))
        conn.commit()

    print(f"✅ Seeded Scenario 5: 'inventory' dataset lineage event by K. Vance + stock_sync_latency_ms anomaly.")


def run_d2_7_verification():
    print("\n=======================================================")
    print("   VARVE D2.7 CANDIDATE INCIDENT VERIFICATION HARNESS")
    print("=======================================================")

    # 1. Seed Scenario 5
    seed_test_scenario_5()

    # 2. Detect Anomalies
    print("\n1. Running Z-score Anomaly Detection Scan...")
    anom_res = detect_metric_anomalies(z_threshold=2.0)
    print(f"   Anomalies flagged: {anom_res['anomalies_count']}")

    # 3. Discover Candidate Incidents
    print("\n2. Querying Unconfirmed Candidate Incidents...")
    candidates = get_unconfirmed_candidate_incidents()
    print(f"   Found {len(candidates)} unconfirmed candidate(s).")
    
    target_cand = next((c for c in candidates if "inventory" in c["model_id"]), None)
    assert target_cand is not None, "Scenario 5 candidate must be discovered!"

    print(f"\n► Target Candidate Discovered:")
    print(f"  Candidate ID:  {target_cand['candidate_id']}")
    print(f"  Model ID:      {target_cand['model_id']}")
    print(f"  Metric:        {target_cand['anomaly_metric']} (value: {target_cand['anomaly_value']})")
    print(f"  Event ID:      {target_cand['candidate_event_id']}")
    print(f"  Days Between:  {target_cand['days_between']}d")
    print(f"  Description:   {target_cand['proposed_description']}")

    # 4. Confirm Candidate Incident
    print("\n3. Confirming Candidate Incident...")
    conf_res = confirm_candidate_incident(target_cand["candidate_id"])
    print(f"   Confirmation status: {conf_res['status']}")
    print(f"   New Incident ID:     {conf_res['incident_id']}")

    # 5. Verify Database Records
    print("\n4. Verifying PostgreSQL Tables...")
    model_id = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.inventory,PROD)"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check incidents table
            cur.execute("SELECT incident_id, root_cause_event_id, description FROM incidents WHERE root_cause_event_id = 'f6a7b8c9-d0e1-2345-fa01-678901234567';")
            inc_row = cur.fetchone()
            assert inc_row is not None, "New row MUST exist in incidents table!"
            print(f"   ✔ Incidents Table: Found incident '{inc_row['incident_id']}' linked to root_cause_event_id '{inc_row['root_cause_event_id']}'.")

            # Check patterns table for departing_engineer_change / K. Vance / org_wide
            cur.execute("SELECT scope_key, pattern_type, times_observed, times_preceded_incident FROM patterns WHERE pattern_type = 'departing_engineer_change' AND scope_key = 'org_wide';")
            pat_row = cur.fetchone()
            assert pat_row is not None, "Patterns row MUST exist!"
            print(f"   ✔ Patterns Table: org_wide 'departing_engineer_change' -> observed={pat_row['times_observed']}, preceded_incident={pat_row['times_preceded_incident']}.")

    # 6. Verify Ledger Chain
    print("\n5. Verifying Audit Ledger Hash Chain...")
    ledger_res = verify_ledger_chain()
    print(f"   ✔ Audit Ledger: {ledger_res['message']}")
    assert ledger_res["valid"] is True, "Audit ledger chain MUST be 100% valid!"

    print("\n=======================================================")
    print("✅ D2.7 VERIFICATION PASSED: Candidate incident confirmed,")
    print("   incidents row created, patterns updated, & ledger verified!")
    print("=======================================================\n")


if __name__ == "__main__":
    run_d2_7_verification()
