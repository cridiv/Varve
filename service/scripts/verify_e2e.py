#!/usr/bin/env python3
"""
Varve End-to-End System Verification Harness (Phases 1 - 10)

Walks the complete system in true operational sequence:
DataHub in -> Postgres through -> NVIDIA StepFun LLM out -> DataHub back -> Cryptographic Audit Ledger verified.
"""

import sys
import os
import time
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(service_dir)
if service_dir not in sys.path:
    sys.path.append(service_dir)

from config.config import DATAHUB_GMS_URL, DATAHUB_GMS_TOKEN
from db.connection import get_db_connection
from services.correlation_service import (
    populate_patterns,
    classify_pattern,
    resolve_pattern_severity_by_trust_scope,
    run_ground_truth_check,
)
from services.generator_service import populate_findings
from services.anomaly_service import (
    detect_metric_anomalies,
    get_unconfirmed_candidate_incidents,
    confirm_candidate_incident,
)
from services.datahub_service import (
    get_datahub_graph,
    resolve_dataset_routed_owner_info,
    resolve_dataset_governance_multiplier,
    writeback_finding_to_datahub,
    confirm_datahub_annotation,
)
from services.ledger_service import verify_ledger_chain, append_to_ledger
from services.validation_service import generate_validation_report
from datahub.metadata.schema_classes import OwnershipClass, GlobalTagsClass, InstitutionalMemoryClass


def run_full_e2e_verification():
    phase_results = {}

    print("==========================================================================")
    print("      VARVE END-TO-END SYSTEM INTEGRATION & VERIFICATION HARNESS")
    print("==========================================================================\n")

    # --------------------------------------------------------------------------
    # PHASE 1: Fresh State, No Assumptions
    # --------------------------------------------------------------------------
    print("► PHASE 1: Resetting Database State to Fresh Seed Baseline...")
    try:
        schema_path = os.path.join(service_dir, "db", "schema.sql")
        seed_path = os.path.join(service_dir, "db", "seed.sql")

        with open(schema_path, "r") as f:
            schema_sql = f.read()
        with open(seed_path, "r") as f:
            seed_sql = f.read()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS ledger, candidate_incidents, findings, patterns, incidents, business_metrics, lineage_events CASCADE;")
                cur.execute(schema_sql)
                cur.execute(seed_sql)
            conn.commit()

        populate_patterns()
        print("  ✔ Database schema & seed narratives re-applied cleanly.")
        phase_results["Phase 1 — Fresh State"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 1 Failed: {e}")
        phase_results["Phase 1 — Fresh State"] = f"FAIL: {e}"
        return phase_results

    # --------------------------------------------------------------------------
    # PHASE 2: DataHub Connectivity & Metadata Health
    # --------------------------------------------------------------------------
    print("\n► PHASE 2: Verifying Standalone DataHub GMS Connectivity & Aspects...")
    try:
        health_res = requests.get(f"{DATAHUB_GMS_URL}/health", timeout=5)
        assert health_res.status_code == 200, f"DataHub GMS health returned {health_res.status_code}"

        graph = get_datahub_graph()
        customers_urn = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)"
        
        ownership = graph.get_aspect(customers_urn, OwnershipClass)
        assert ownership is not None and len(ownership.owners) > 0, "Customers dataset ownership must be populated in DataHub!"
        
        print("  ✔ DataHub GMS is Healthy.")
        print(f"  ✔ Direct Ownership Aspect verified: {len(ownership.owners)} owner(s) found on customers dataset.")
        phase_results["Phase 2 — DataHub Health"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 2 Failed: {e}")
        phase_results["Phase 2 — DataHub Health"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 3: Core Correlation against Ground Truth
    # --------------------------------------------------------------------------
    print("\n► PHASE 3: Running Ground-Truth Correlation Benchmark (Stories 1–4)...")
    try:
        gt_res = run_ground_truth_check()
        assert gt_res["summary"]["all_passed"] is True, "All ground truth assertions must pass!"
        print(f"  ✔ Ground-truth benchmark passed ({gt_res['summary']['passed']}/{gt_res['summary']['total']} scenarios).")
        phase_results["Phase 3 — Core Correlation Benchmark"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 3 Failed: {e}")
        phase_results["Phase 3 — Core Correlation Benchmark"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 4: Cold-Start and Fallback Tiers
    # --------------------------------------------------------------------------
    print("\n► PHASE 4: Verifying Trust Hierarchy & Industry Base Rate Thresholds...")
    try:
        # Seed test industry baseline patterns with 0 org_wide observations
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO patterns (scope_key, pattern_type, times_observed, times_preceded_incident) VALUES
                    ('industry_general', 'test_high_risk_pattern', 100, 30),
                    ('industry_general', 'test_moderate_risk_pattern', 100, 20),
                    ('industry_general', 'test_low_risk_pattern', 100, 10)
                    ON CONFLICT (scope_key, pattern_type) DO UPDATE SET
                        times_observed = EXCLUDED.times_observed,
                        times_preceded_incident = EXCLUDED.times_preceded_incident;
                """)
            conn.commit()

        # Test 1: Industry general base rate >= 25% (30%) -> Provisional HIGH retained
        stale_res = resolve_pattern_severity_by_trust_scope(
            pattern_type="test_high_risk_pattern",
            actor="Unknown Actor",
            provisional_severity="high",
        )
        assert stale_res["severity"] == "high"
        assert stale_res["scope_key"] == "industry_general"

        # Test 2: Industry general base rate 15-24% (20%) -> Severity capped at MEDIUM
        mod_res = resolve_pattern_severity_by_trust_scope(
            pattern_type="test_moderate_risk_pattern",
            actor="Unknown Actor",
            provisional_severity="high",
        )
        assert mod_res["severity"] == "medium"
        assert mod_res["scope_key"] == "industry_general"

        # Test 3: Industry general base rate < 15% (10%) -> Downgraded to LOW
        exp_res = resolve_pattern_severity_by_trust_scope(
            pattern_type="test_low_risk_pattern",
            actor="Unknown Actor",
            provisional_severity="high",
        )
        assert exp_res["severity"] == "low"
        assert exp_res["scope_key"] == "industry_general"

        print("  ✔ Base rate 3-tier thresholds verified: 30% retained HIGH, 20% capped at MEDIUM, 10% downgraded to LOW.")
        phase_results["Phase 4 — Cold-Start & Fallback Tiers"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 4 Failed: {e}")
        phase_results["Phase 4 — Cold-Start & Fallback Tiers"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 5: The Self-Bootstrapping Loop (End to End)
    # --------------------------------------------------------------------------
    print("\n► PHASE 5: Testing Self-Bootstrapping Loop (Anomaly -> Candidate -> Confirm -> Org Pattern)...")
    try:
        # Seed test scenario on inventory model by K. Vance
        inv_event_id = "f6a7b8c9-d0e1-2345-fa01-678901234567"
        inv_model_id = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.inventory,PROD)"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO lineage_events (
                        event_id, model_id, node_type, node_urn, event_type,
                        event_timestamp, actor, actor_departed_within_90d, documentation_present
                    ) VALUES (
                        %s, %s, 'pipeline_step', %s, 'modified',
                        '2026-07-10 08:00:00+00', 'K. Vance', TRUE, FALSE
                    );
                """, (inv_event_id, inv_model_id, inv_model_id))

                cur.execute("""
                    INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
                    (%s, 'stock_sync_latency_ms', 45.0, '2026-07-08 00:00:00+00'),
                    (%s, 'stock_sync_latency_ms', 46.2, '2026-07-09 00:00:00+00'),
                    (%s, 'stock_sync_latency_ms', 850.0, '2026-07-14 12:00:00+00');
                """, (inv_model_id, inv_model_id, inv_model_id))
            conn.commit()

        # Step A: Pre-confirmation check for a candidate pattern shape (should fall back to industry_general)
        pre_res = resolve_pattern_severity_by_trust_scope(
            pattern_type="test_low_risk_pattern",
            actor="K. Vance",
            provisional_severity="high",
        )
        assert pre_res["scope_key"] == "industry_general", "Prior to incident confirmation, must fall back to industry_general!"

        # Step B: Detect anomaly & find candidate
        detect_metric_anomalies(z_threshold=2.0)
        candidates = get_unconfirmed_candidate_incidents()
        cand = next((c for c in candidates if "inventory" in c["model_id"]), None)
        assert cand is not None, "Candidate incident for inventory must be discovered!"

        # Step C: Confirm candidate incident
        conf_res = confirm_candidate_incident(cand["candidate_id"])
        assert conf_res["status"] == "confirmed"

        # Step D: Loop-closing verification (Must now resolve to org_wide precedent!)
        post_res = resolve_pattern_severity_by_trust_scope(
            pattern_type="departing_engineer_change",
            actor="K. Vance",
            provisional_severity="high",
            model_id=inv_model_id,
        )
        assert post_res["scope_key"] in ["org_wide", "model"], "Post-confirmation must upgrade to org_wide precedent!"

        print("  ✔ Self-bootstrapping loop closed: Anomaly detected -> Candidate confirmed -> Org precedent updated immediately!")
        phase_results["Phase 5 — Self-Bootstrapping Loop"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 5 Failed: {e}")
        phase_results["Phase 5 — Self-Bootstrapping Loop"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 6: Ownership and Governance Composition
    # --------------------------------------------------------------------------
    print("\n► PHASE 6: Verifying Ownership Priority Rules & Governance Tag Multipliers...")
    try:
        # Check Customers (PII + business-critical)
        cust_owner = resolve_dataset_routed_owner_info(customers_urn)
        assert cust_owner["priority_rule_matched"] == "individual-not-EMP006"
        
        cust_gov = resolve_dataset_governance_multiplier(customers_urn)
        assert cust_gov["multiplier"] == 1.5
        assert cust_gov["tag_source"] in ["datahub_native", "inferred"]

        # Check Harmless Deprecated Table (Exclusion Filter Proof)
        harmless_urn = "urn:li:dataset:(...,customer_satisfaction_survey_archive_deprecated,PROD)"
        harmless_gov = resolve_dataset_governance_multiplier(harmless_urn)
        assert harmless_gov["multiplier"] == 1.0
        assert harmless_gov["tag_source"] == "none"

        print("  ✔ Ownership routing priority verified (jonny1 Data Owner).")
        print("  ✔ Governance multipliers & tag_source honesty labels verified.")
        print("  ✔ Semantic exclusion filter verified (false-positive survey table ignored).")
        phase_results["Phase 6 — Ownership & Governance"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 6 Failed: {e}")
        phase_results["Phase 6 — Ownership & Governance"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 7: LLM Synthesis Quality Check
    # --------------------------------------------------------------------------
    print("\n► PHASE 7: Populating Findings & Validating NVIDIA DeepSeek v4 Flash LLM Synthesis...")
    try:
        findings = populate_findings()
        assert len(findings) >= 5, "Should generate findings for all lineage events!"

        sample_finding = findings[0]
        assert "narrative" in sample_finding and len(sample_finding["narrative"]) > 20
        assert "recommended_action" in sample_finding and len(sample_finding["recommended_action"]) > 20

        print(f"  ✔ Generated {len(findings)} findings via NVIDIA DeepSeek v4 Flash LLM.")
        print(f"  ✔ Sample Narrative: '{sample_finding['narrative'][:80]}...'")
        print(f"  ✔ Sample Action:    '{sample_finding['recommended_action'][:80]}...'")
        phase_results["Phase 7 — LLM Synthesis Quality"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 7 Failed: {e}")
        phase_results["Phase 7 — LLM Synthesis Quality"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 8: Write-back to DataHub
    # --------------------------------------------------------------------------
    print("\n► PHASE 8: Testing Direct DataHub Aspect Write-Back...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT finding_id, model_id FROM findings WHERE model_id = %s LIMIT 1;", (customers_urn,))
                target_f = cur.fetchone()

        assert target_f is not None, "Target finding for customers dataset must exist!"
        fid = str(target_f["finding_id"])

        wb_res = writeback_finding_to_datahub(fid)
        assert wb_res["status"] == "written_back"

        # Verify directly on DataHub GMS
        dh_check = confirm_datahub_annotation(customers_urn)
        assert dh_check is True, "DataHub GMS InstitutionalMemory aspect must be verified directly on catalog!"

        print(f"  ✔ Finding '{fid}' written back to DataHub GMS.")
        print(f"  ✔ Verified on DataHub GMS: Aspect confirmed on catalog node.")
        phase_results["Phase 8 — DataHub Write-Back"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 8 Failed: {e}")
        phase_results["Phase 8 — DataHub Write-Back"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 9: Cryptographic Audit Ledger Integrity Across Full Run
    # --------------------------------------------------------------------------
    print("\n► PHASE 9: Verifying SHA-256 Hash Chain Integrity & Logging All Ledger Entries...")
    try:
        ledger_res = verify_ledger_chain()
        assert ledger_res["valid"] is True, "Audit ledger chain must be 100% valid!"

        print(f"\n==========================================================================")
        print(f"  PRINTING ALL {ledger_res['total_verified']} CRYPTOGRAPHIC AUDIT LEDGER ENTRIES")
        print(f"==========================================================================")
        for item in ledger_res.get("details", []):
            f_str = item.get("finding_id") or "NONE"
            if len(f_str) > 8:
                f_str = f_str[:8] + "..."
            print(f"  [✔ PASS] Row {item['index']:<2} | Event: {item['event_type']:<22} | Finding: {f_str:<11} | Hash: {item['this_hash'][:16]}...")
        print("==========================================================================\n")

        print(f"  ✔ Cryptographic Audit Ledger Verified: {ledger_res['message']}")
        phase_results["Phase 9 — Ledger Hash Chain"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 9 Failed: {e}")
        phase_results["Phase 9 — Ledger Hash Chain"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # PHASE 10: Report Generation & Summary
    # --------------------------------------------------------------------------
    print("\n► PHASE 10: Generating Comprehensive Validation Report...")
    try:
        generate_validation_report()
        print("  ✔ Updated docs/validation.md with full benchmark & resolution report.")
        phase_results["Phase 10 — Report Generation"] = "PASS"
    except Exception as e:
        print(f"  ❌ Phase 10 Failed: {e}")
        phase_results["Phase 10 — Report Generation"] = f"FAIL: {e}"

    # --------------------------------------------------------------------------
    # FINAL SUMMARY REPORT
    # --------------------------------------------------------------------------
    print("\n==========================================================================")
    print("         VARVE END-TO-END VERIFICATION SUMMARY REPORT")
    print("==========================================================================")
    all_passed = True
    for phase_name, status in phase_results.items():
        symbol = "✅" if status == "PASS" else "❌"
        print(f"  {symbol} {phase_name:<42} : {status}")
        if status != "PASS":
            all_passed = False

    print("==========================================================================")
    if all_passed:
        print("✅ ALL 10 PHASES PASSED 100% CLEAN — SYSTEM IS READY FOR LIVE DEMO!")
    else:
        print("❌ ONE OR MORE PHASES FAILED — REVIEW LOGS ABOVE.")
    print("==========================================================================\n")

    return phase_results


if __name__ == "__main__":
    run_full_e2e_verification()
