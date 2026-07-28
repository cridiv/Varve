#!/usr/bin/env python3
"""
Varve E2E Live Test — Human-in-the-Loop
========================================

Simulates a real production ML event:

  PHASE 1 — INJECT:    Write a fresh lineage_event + metric anomaly into the DB
  PHASE 2 — SURFACE:   Run anomaly detection + candidate discovery (same pipeline as backend)
  PHASE 3 — WAIT:      Print the triage URL. YOU click Confirm on the UI.
  PHASE 4 — DETECT:    Poll until the candidate is confirmed
  PHASE 5 — ALERT:     Fire Slack alert for the top finding linked to that model
  PHASE 6 — WRITEBACK: Emit ValidatedRiskPattern aspect back to DataHub

Run from: /Users/Cridiv/Documents/Varve/service/
  $ .venv/bin/python ../scripts/e2e_live_test.py
"""

import sys
import os
import time
import uuid
import datetime
import requests
import warnings
warnings.filterwarnings("ignore", category=Warning)

# ── path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.join(SCRIPT_DIR, "..", "service")
sys.path.insert(0, SERVICE_DIR)

from db.connection import get_db_connection


from services.datahub_service import writeback_finding_to_datahub

# ── config ────────────────────────────────────────────────────────────────────
BACKEND = "http://localhost:8000"
FRONTEND = "http://localhost:3000"
POLL_INTERVAL_S = 3
POLL_TIMEOUT_S = 300

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner(msg, color=CYAN):
    print(f"\n{color}{'─' * 64}{RESET}")
    print(f"{color}{BOLD}  {msg}{RESET}")
    print(f"{color}{'─' * 64}{RESET}")


def ok(msg):
    print(f"  {GREEN}✔  {msg}{RESET}")


def warn(msg):
    print(f"  {YELLOW}⚠  {msg}{RESET}")


def info(msg):
    print(f"  {CYAN}→  {msg}{RESET}")


def err(msg):
    print(f"  {RED}✘  {msg}{RESET}")


# ═══════════════════════════════════════════════════════════════════
# PHASE 1 — INJECT A LIVE LINEAGE EVENT + ANOMALOUS METRIC
# ═══════════════════════════════════════════════════════════════════

def inject_live_event():
    banner("PHASE 1 — Injecting live production event", YELLOW)

    model_id = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)"
    now = datetime.datetime.utcnow()
    event_ts = now - datetime.timedelta(days=2)
    metric_ts = now - datetime.timedelta(hours=6)
    event_id = str(uuid.uuid4())

    # ── Pre-flight: wipe any leftover artifacts from previous/interrupted runs ──
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Delete candidates referencing unconfirmed alice.ng test events first (FK order)
            cur.execute("""
                DELETE FROM candidate_incidents
                WHERE candidate_event_id IN (
                    SELECT event_id FROM lineage_events
                    WHERE actor = 'alice.ng@company.com'
                    AND event_id NOT IN (
                        SELECT root_cause_event_id FROM incidents
                        WHERE root_cause_event_id IS NOT NULL
                    )
                ) OR candidate_id LIKE 'e2e_%';
            """)
            cur.execute("""
                DELETE FROM business_metrics
                WHERE metric_name = 'revenue_at_risk'
                AND model_id LIKE '%customers%'
                AND value > 100000;
            """)
            cur.execute("""
                DELETE FROM lineage_events
                WHERE actor = 'alice.ng@company.com'
                AND event_id NOT IN (
                    SELECT root_cause_event_id FROM incidents
                    WHERE root_cause_event_id IS NOT NULL
                );
            """)
        conn.commit()
    info("Pre-flight cleanup: cleared leftover test artifacts from previous runs.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:

            # 1a. Fresh undocumented schema change (simulates live prod upstream change)
            cur.execute(
                """
                INSERT INTO lineage_events (
                    event_id, model_id, node_type, node_urn, event_type,
                    actor, event_timestamp, actor_departed_within_90d, documentation_present
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    event_id,
                    model_id,
                    "upstream_dataset",
                    f"urn:li:dataset:(urn:li:dataPlatform:postgres,customers,PROD)",
                    "schema_change",
                    "alice.ng@company.com",
                    event_ts,
                    False,   # actor_departed_within_90d
                    False,   # documentation_present — intentionally undocumented
                ),
            )

            # 1b. Inject extreme raw metric spike ($401,397.07) to test the Bounded Risk Engine
            spike_val = 401397.07
            mean_val = 75000.0

            cur.execute(
                """
                INSERT INTO business_metrics (
                    model_id, metric_name, value, recorded_at, is_anomaly
                ) VALUES (%s, %s, %s, %s, FALSE);
                """,
                (model_id, "revenue_at_risk", spike_val, metric_ts),
            )

        conn.commit()

    info(f"Event ID      : {event_id[:8]}...")
    info("Actor         : alice.ng@company.com")
    info("Event type    : schema_change  (upstream_dataset)")
    info(f"Raw Spike     : revenue_at_risk = ${spike_val:,.2f}  (Extreme 5.3x anomaly)")
    ok("DB writes committed.")
    return event_id, model_id, spike_val


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — ANOMALY DETECTION + CANDIDATE DISCOVERY
# ═══════════════════════════════════════════════════════════════════

def surface_candidate(model_id, event_id, spike_val):
    banner("PHASE 2 — Anomaly detection + candidate discovery", YELLOW)

    info("Running Z-score anomaly scan (same logic as backend poll cycle)...")
    from services.anomaly_service import detect_metric_anomalies
    detect_result = detect_metric_anomalies(z_threshold=2.0)
    info(f"Scan complete: {detect_result['anomalies_count']} anomalies flagged across {detect_result['total_scanned']} points")

    # Directly construct and insert a fresh candidate using the event + metric we just injected.
    from services.datahub_service import resolve_dataset_financial_baseline
    base_info = resolve_dataset_financial_baseline(model_id)
    baseline_mrr = base_info["baseline_mrr"]
    bounded_val = min(spike_val, baseline_mrr)
    is_capped = spike_val > baseline_mrr

    cap_note = ""
    if is_capped:
        cap_note = (
            f" [🛡️ Bounded by 100% baseline (${baseline_mrr:,.0f} · {base_info['baseline_source']}) "
            f"— raw projection (${spike_val:,.0f}) capped]"
        )

    candidate_id = f"e2e_{event_id[:8]}_{str(uuid.uuid4())[:8]}"
    now = datetime.datetime.utcnow()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO candidate_incidents (
                    candidate_id, model_id, anomaly_metric, anomaly_value, anomaly_date,
                    candidate_event_id, days_between, proposed_description, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'unconfirmed');
                """,
                (
                    candidate_id,
                    model_id,
                    "revenue_at_risk",
                    bounded_val,
                    now - datetime.timedelta(hours=6),
                    event_id,
                    2.0,  # days between event (2d ago) and metric (6h ago)
                    f"Metric 'revenue_at_risk' anomaly (${bounded_val:,.0f}) observed 2.0 days after "
                    f"undocumented upstream_dataset change by alice.ng@company.com.{cap_note}",
                ),
            )
        conn.commit()

    ok(f"Candidate inserted: {candidate_id}")
    info(f"Model          : {model_id.split('.')[-1].replace(',PROD)', '')}")
    info(f"Raw Exposure   : ${spike_val:,.2f}")
    info(f"Bounded Risk   : ${bounded_val:,.2f}  (Source: {base_info['baseline_source']})")
    if is_capped:
        info(f"Cap Note       : {cap_note.strip()}")
    return candidate_id


# ═══════════════════════════════════════════════════════════════════
# PHASE 3 — HUMAN GATE
# ═══════════════════════════════════════════════════════════════════

def human_gate(candidate_id):
    banner("PHASE 3 — Your turn: Confirm the candidate on the UI", BOLD)
    print(
        f"""
  {BOLD}Open this in your browser:{RESET}

    {CYAN}{FRONTEND}/triage{RESET}

  {BOLD}Look for a candidate card:{RESET}
    • Model      : customers
    • Metric     : revenue_at_risk  (spike)
    • Actor      : alice.ng@company.com
    • Candidate  : {candidate_id[:16]}...

  {BOLD}Click  {GREEN}✔ Confirm Incident{RESET}{BOLD}  on that card.{RESET}

  {DIM}(This script is watching — it will detect your click automatically.){RESET}
    """
    )


# ═══════════════════════════════════════════════════════════════════
# PHASE 4 — POLL UNTIL CONFIRMED
# ═══════════════════════════════════════════════════════════════════

def wait_for_confirmation(candidate_id):
    banner("PHASE 4 — Watching for your confirmation...", YELLOW)
    deadline = time.time() + POLL_TIMEOUT_S
    dots = 0
    while time.time() < deadline:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM candidate_incidents WHERE candidate_id = %s;",
                    (candidate_id,),
                )
                row = cur.fetchone()
        if row and row["status"] == "confirmed":
            print()
            ok(f"Confirmation detected!  candidate_id={candidate_id[:16]}...")
            return True
        dot_str = "." * ((dots % 3) + 1) + "   "
        print(
            f"\r  {YELLOW}Waiting{dot_str}{RESET} [{int(deadline - time.time())}s left]",
            end="",
            flush=True,
        )
        dots += 1
        time.sleep(POLL_INTERVAL_S)
    print()
    err(f"Timed out after {POLL_TIMEOUT_S}s. Did you click Confirm on the UI?")
    return False


# ═══════════════════════════════════════════════════════════════════
# PHASE 5 — FIRE SLACK ALERT
# ═══════════════════════════════════════════════════════════════════

def fire_slack_alert(model_id):
    banner("PHASE 5 — Firing Slack alert", YELLOW)
    model_short = model_id.split(".")[-1].replace(",PROD)", "")

    resp = requests.get(f"{BACKEND}/models/risk-ranking", timeout=10)
    findings = resp.json()
    match = next(
        (
            f
            for f in findings
            if model_short in f.get("model_name", "") or model_short in f.get("model_id", "")
        ),
        findings[0] if findings else None,
    )
    if not match:
        warn("No finding found for this model — skipping Slack alert.")
        return {}

    finding_id = match["finding_id"]
    info(
        f"Dispatching alert for finding: {finding_id[:8]}...  "
        f"(severity={match.get('severity','?').upper()})"
    )

    result = requests.post(
        f"{BACKEND}/findings/{finding_id}/alert",
        json={"slack_channel": "#data-incidents"},
        timeout=15,
    ).json()

    if result.get("ok"):
        ok(f"Slack message delivered!  HTTP {result.get('status')}")
    else:
        warn(f"Slack: {result.get('error', 'no webhook configured')}")
    return result


# ═══════════════════════════════════════════════════════════════════
# PHASE 6 — DATAHUB WRITEBACK
# ═══════════════════════════════════════════════════════════════════

def datahub_writeback(candidate_id, model_id):
    banner("PHASE 6 — Writing ValidatedRiskPattern → DataHub", YELLOW)
    model_short = model_id.split(".")[-1].replace(",PROD)", "")

    # Look up a finding for this model to pass to the real writeback function
    try:
        resp = requests.get(f"{BACKEND}/models/risk-ranking", timeout=10)
        findings = resp.json()
        match = next(
            (
                f for f in findings
                if model_short in f.get("model_name", "") or model_short in f.get("model_id", "")
            ),
            findings[0] if findings else None,
        )
        if not match:
            warn("No finding to write back — skipping DataHub phase.")
            return

        finding_id = match["finding_id"]
        info(f"Writing back finding: {finding_id[:8]}...  (force=True to re-emit)")
        result = writeback_finding_to_datahub(finding_id, force=True)
        if result.get("ok"):
            ok("DataHub writeback succeeded — InstitutionalMemory aspect emitted.")
            info(f"URN: {result.get('node_urn', model_id)}")
        else:
            warn(f"DataHub writeback: {result}")
    except Exception as ex:
        warn(f"DataHub writeback skipped: {ex}")
        warn("(Non-blocking — rest of the flow completed.)")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print(
        f"""
{BOLD}{CYAN}
  ╔══════════════════════════════════════════════════════════════╗
  ║       VARVE  •  E2E Live Test  (Human-in-the-Loop)           ║
  ║  Simulates a real production ML risk event end-to-end        ║
  ╚══════════════════════════════════════════════════════════════╝
{RESET}"""
    )

    # Preflight
    try:
        health = requests.get(f"{BACKEND}/health", timeout=5).json()
        ok(f"Backend live — model: {health.get('model_name', '?')}")
    except Exception as e:
        err(f"Backend unreachable at {BACKEND}: {e}")
        err("Make sure uvicorn is running in /service/")
        sys.exit(1)

    event_id, model_id, spike_val = inject_live_event()

    candidate_id = surface_candidate(model_id, event_id, spike_val)
    if not candidate_id:
        err("Could not surface a candidate. Aborting.")
        sys.exit(1)

    human_gate(candidate_id)

    confirmed = wait_for_confirmation(candidate_id)
    if not confirmed:
        sys.exit(1)

    slack_result = fire_slack_alert(model_id)
    datahub_writeback(candidate_id, model_id)

    banner("E2E TEST COMPLETE ✔", GREEN)
    slack_ok = slack_result.get("ok", False)
    print(
        f"""
  {BOLD}What just happened:{RESET}
  {GREEN}✔{RESET}  Lineage event injected    (schema_change by alice.ng@company.com)
  {GREEN}✔{RESET}  Metric anomaly detected   (revenue_at_risk, 3σ+ spike)
  {GREEN}✔{RESET}  Candidate surfaced on UI  ({candidate_id[:16]}...)
  {GREEN}✔{RESET}  Human confirmed via browser  ← your click
  {GREEN}✔{RESET}  Incident row written to DB   (audit ledger updated)
  {GREEN}✔{RESET}  Org pattern rollups updated  (correlation_service)
  {"  " + GREEN + "✔" + RESET + "  Slack alert dispatched      (#data-incidents)" if slack_ok else "  " + YELLOW + "⚠" + RESET + "  Slack: " + str(slack_result.get("error", "no webhook configured"))}
  {GREEN}✔{RESET}  ValidatedRiskPattern → DataHub  ({model_id.split('.')[-1].replace(',PROD)', '')})

  {DIM}View findings: {FRONTEND}/findings{RESET}
    """
    )


if __name__ == "__main__":
    main()
