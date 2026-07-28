"""One-shot cleanup: removes all phantom candidates and test metric spikes from DB."""
import sys
sys.path.insert(0, "/Users/Cridiv/Documents/Varve/service")
from db.connection import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 1. All unconfirmed candidates that are NOT the e2e_ ones
        cur.execute("""
            DELETE FROM candidate_incidents
            WHERE status = 'unconfirmed'
            AND candidate_id NOT LIKE 'e2e_%';
        """)
        a = cur.rowcount

        # 2. All test metric spikes — revenue_at_risk > 100k on customers (all synthetic)
        cur.execute("""
            DELETE FROM business_metrics
            WHERE metric_name = 'revenue_at_risk'
            AND model_id LIKE '%customers%'
            AND value > 100000;
        """)
        b = cur.rowcount

        # 3. Orphan lineage events from alice.ng not referenced by confirmed incidents
        cur.execute("""
            DELETE FROM lineage_events
            WHERE actor = 'alice.ng@company.com'
            AND event_id NOT IN (
                SELECT root_cause_event_id FROM incidents
                WHERE root_cause_event_id IS NOT NULL
            );
        """)
        c = cur.rowcount

    conn.commit()

print(f"Deleted: {a} phantom candidates | {b} test metric rows | {c} orphan lineage events")

# Verify
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as n FROM candidate_incidents WHERE status='unconfirmed';")
        n = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) as cnt, AVG(value) as avg FROM business_metrics WHERE metric_name='revenue_at_risk' AND model_id LIKE '%customers%';")
        r = cur.fetchone()
        print(f"Remaining unconfirmed candidates : {n}")
        print(f"Remaining revenue_at_risk metrics: {r['cnt']} rows, avg=${float(r['avg'] or 0):,.0f}")
