"""
Varve Correlation Engine — Tier 1 (Per-Model Correlation & Pattern Classification)

Step 5.1, 5.2, 5.3, 5.4 implementation:
- get_matching_incidents_for_event(event_id): Query incidents linked by root_cause_event_id.
- classify_pattern(event_id): Classify event as validated/unvalidated and assign severity.
- run_ground_truth_check(): End-to-end verification against seeded test events.
"""

import sys
import os
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from psycopg2.extras import RealDictCursor
from config.config import POSTGRES_DSN


def get_db_connection():
    """Returns a new psycopg2 database connection."""
    return psycopg2.connect(POSTGRES_DSN, cursor_factory=RealDictCursor)


def get_matching_incidents_for_event(event_id: str) -> List[Dict[str, Any]]:
    """
    Step 5.1: Given a lineage_events.event_id, look up incidents where
    root_cause_event_id matches. Return whichever incidents match.
    """
    query = """
        SELECT 
            incident_id,
            model_id,
            detected_at,
            resolved_at,
            root_cause_event_id,
            description,
            fix_summary
        FROM incidents
        WHERE root_cause_event_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (event_id,))
            rows = cur.fetchall()
            # Convert RealDictRow to standard dicts
            return [dict(r) for r in rows]


def classify_pattern(event_id: str) -> Dict[str, Any]:
    """
    Step 5.3: Wrap correlation lookup into a pattern classification rule:
    - If a matched incident exists: validated = True, severity = 'high'
    - Otherwise: validated = False, severity = 'low'
    """
    # Fetch event details first
    event_query = """
        SELECT event_id, model_id, node_type, actor, event_timestamp, documentation_present
        FROM lineage_events
        WHERE event_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(event_query, (event_id,))
            event = cur.fetchone()

    if not event:
        raise ValueError(f"Lineage event '{event_id}' not found in database.")

    event = dict(event)
    matched_incidents = get_matching_incidents_for_event(event_id)

    is_validated = len(matched_incidents) > 0
    severity = "high" if is_validated else "low"

    # Derive pattern type based on event characteristics
    if not event["documentation_present"] and event["node_type"] == "threshold":
        pattern_type = "departing_engineer_change" if is_validated else "stale_threshold"
    else:
        pattern_type = "unreviewed_change"

    return {
        "event_id": str(event["event_id"]),
        "model_id": event["model_id"],
        "actor": event["actor"],
        "node_type": event["node_type"],
        "pattern_type": pattern_type,
        "validated": is_validated,
        "severity": severity,
        "matched_incidents": matched_incidents,
        "incident_count": len(matched_incidents),
    }


def run_ground_truth_check() -> List[Dict[str, Any]]:
    """
    Step 5.2 & 5.4: Run classification against all seeded events and confirm
    the validated/unvalidated split matching seed-narrative.md.
    """
    query = "SELECT event_id, actor, model_id FROM lineage_events ORDER BY event_timestamp;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            events = [dict(r) for r in cur.fetchall()]

    print(f"\n=======================================================")
    print(f"   VARVE CORRELATION ENGINE — GROUND TRUTH VERIFICATION")
    print(f"=======================================================")
    print(f"Total seeded events evaluated: {len(events)}\n")

    results = []
    for ev in events:
        classification = classify_pattern(str(ev["event_id"]))
        results.append(classification)

        print(f"► Event ID:     {classification['event_id']}")
        print(f"  Actor:        {classification['actor']}")
        print(f"  Model URN:    {classification['model_id']}")
        print(f"  Pattern Type: {classification['pattern_type']}")
        print(f"  Validated:    {classification['validated']}")
        print(f"  Severity:     {classification['severity']}")
        print(f"  Incidents:    {classification['incident_count']} matched")
        if classification["matched_incidents"]:
            inc = classification["matched_incidents"][0]
            print(f"    - Incident ID:   {inc['incident_id']}")
            print(f"    - Target Model:  {inc['model_id']}")
            print(f"    - Description:   {inc['description']}")
        print("-------------------------------------------------------")

    # Step 5.4 Ground Truth Assertions
    story1_matches = [r for r in results if r["actor"] == "J. Alvarez"]
    story2_matches = [r for r in results if r["actor"] == "R. Chen"]

    assert len(story1_matches) == 1, "Story 1 event for J. Alvarez not found"
    assert story1_matches[0]["validated"] is True, "Story 1 should be validated = True"
    assert story1_matches[0]["severity"] == "high", "Story 1 should have severity = 'high'"
    assert len(story1_matches[0]["matched_incidents"]) == 1, "Story 1 should match exactly 1 incident"

    assert len(story2_matches) == 1, "Story 2 event for R. Chen not found"
    assert story2_matches[0]["validated"] is False, "Story 2 should be validated = False"
    assert story2_matches[0]["severity"] == "low", "Story 2 should have severity = 'low'"
    assert len(story2_matches[0]["matched_incidents"]) == 0, "Story 2 should match 0 incidents"

    print("\n✅ GROUND TRUTH PASSED: All correlation assertions match seed-narrative.md perfectly!")
    return results


if __name__ == "__main__":
    run_ground_truth_check()
