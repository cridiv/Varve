"""
Varve Generator Service — Step 6 (LLM Synthesis & Findings Table Population)

Core business logic:
- generate_finding_narrative(classification): calls NVIDIA StepFun API to produce structured narrative.
- populate_findings(): classifies all events, generates LLM narratives, populates findings table.
- verify_findings_table(): inspects stored findings.
"""

import sys
import os
import json
import time
import requests
import concurrent.futures
from typing import Dict, Any, List

service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from openai import OpenAI
from config.config import (
    MODEL_INVOKE_URL,
    MODEL_NAME,
    MODEL_API_KEY,
    MODEL_TEMPERATURE,
    MODEL_TOP_P,
    MODEL_MAX_TOKENS,
)
from db.connection import get_db_connection
from services.correlation_service import classify_pattern
from services.ledger_service import append_to_ledger
from services.datahub_service import (
    resolve_dataset_routed_owner,
    resolve_dataset_routed_owner_info,
    resolve_dataset_governance_multiplier,
    get_lineage_via_agent_context,
)


def get_openai_client() -> OpenAI:
    api_key = MODEL_API_KEY.replace("Bearer ", "").strip() if MODEL_API_KEY else ""
    base_url = MODEL_INVOKE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url.replace("/chat/completions", "")
    return OpenAI(base_url=base_url, api_key=api_key)


FINDING_PROMPT_TEMPLATE = """You are Varve, an AI Risk & Decision Intelligence Engine for production data pipelines and ML models.
Synthesize a concise, highly professional narrative and recommended action for the following classified risk event.

EVENT CLASSIFICATION:
- Model URN: {model_id}
- Lineage Change Node: {node_type}
- Change Actor: {actor}
- Pattern Type: {pattern_type}
- Historically Validated Incident Precedent: {validated}
- Final Severity: {severity}

DATAHUB AGENT CONTEXT (MULTI-HOP ML LINEAGE):
- Retrieved Via: {retrieved_via}
- Upstream Hops Traced: {total_hops}
- Multi-Hop Graph Lineage Path: {lineage_path}

FINANCIAL EXPOSURE BOUNDING CONTEXT:
- Monthly Baseline Volume: ${baseline_mrr:,.0f} (Source: {baseline_source})
- Max Bounded Exposure Value: ${bounded_anomaly_value:,.0f}
{cap_instruction_prompt}

HISTORICAL INCIDENT CONTEXT:
{incident_context}

Output ONLY valid JSON matching this exact structure with no extra keys or surrounding text:
{{
  "narrative": "A concise 2-sentence explanation of why this change pattern is risky or benign based on organizational precedent.",
  "recommended_action": "A clear, actionable 1-sentence remediation step for engineers."
}}"""


def generate_finding_narrative(classification: Dict[str, Any]) -> Dict[str, str]:
    """
    Step 6.1: Calls NVIDIA API with deepseek-ai/deepseek-v4-flash (via OpenAI SDK)
    to generate structured narrative and recommended action for a classified event.
    Includes Regenerate-over-Replace LLM Sanitizer to prevent numeric hallucination.
    """
    from services.datahub_service import resolve_dataset_financial_baseline
    base_info = resolve_dataset_financial_baseline(classification["model_id"])
    baseline_mrr = base_info["baseline_mrr"]
    bounded_anomaly_value = min(float(classification.get("anomaly_value", baseline_mrr)), baseline_mrr)

    cap_instruction = (
        f"CRITICAL CONSTRAINT: Do NOT cite any monetary loss or risk figure exceeding ${baseline_mrr:,.0f}."
    )

    if classification["matched_incidents"]:
        inc = classification["matched_incidents"][0]
        incident_context = (
            f"- Incident ID: {inc['incident_id']}\n"
            f"- Incident Target Model: {inc['model_id']}\n"
            f"- Detection Date: {inc['detected_at']}\n"
            f"- Incident Description: {inc['description']}\n"
            f"- Historical Fix: {inc['fix_summary']}"
        )
    elif classification["cross_model_incidents"]:
        inc = classification["cross_model_incidents"][0]
        incident_context = (
            f"- Cross-Model Incident ID: {inc['incident_id']}\n"
            f"- Origin Model (Event): {inc['origin_model_id']}\n"
            f"- Impacted Incident Model: {inc['incident_model_id']}\n"
            f"- Detection Date: {inc['detected_at']}\n"
            f"- Detection Lag: {inc['detection_lag_days']:.1f} days\n"
            f"- Incident Description: {inc['description']}"
        )
    else:
        incident_context = "No historical incident precedent linked to this change event (Unvalidated control group)."

    lineage_context = get_lineage_via_agent_context(classification["model_id"], max_hops=5)

    prompt = FINDING_PROMPT_TEMPLATE.format(
        model_id=classification["model_id"],
        node_type=classification["node_type"],
        actor=classification["actor"],
        pattern_type=classification["pattern_type"],
        validated="YES" if classification["validated"] else "NO",
        severity=classification["severity"].upper(),
        retrieved_via=lineage_context.get("retrieved_via", "datahub-agent-context"),
        total_hops=lineage_context.get("total_upstream_hops", 1),
        lineage_path=lineage_context.get("lineage_path", "Direct Node"),
        baseline_mrr=baseline_mrr,
        baseline_source=base_info["baseline_source"],
        bounded_anomaly_value=bounded_anomaly_value,
        cap_instruction_prompt=cap_instruction,
        incident_context=incident_context,
    )

    client = get_openai_client()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=MODEL_TEMPERATURE,
                top_p=MODEL_TOP_P,
                max_tokens=MODEL_MAX_TOKENS,
                extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
                stream=False,
            )

            reasoning = (
                getattr(completion.choices[0].message, "reasoning", None)
                or getattr(completion.choices[0].message, "reasoning_content", None)
            )
            if reasoning:
                model_short = classification["model_id"].split(".")[-1].replace(",PROD)", "")
                print(f"🧠 [DeepSeek Reasoning - {model_short}]: {reasoning[:120]}...")

            raw_text = completion.choices[0].message.content.strip()

            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed = json.loads(raw_text)

            # ── Regenerate-Over-Replace Sanitizer ──────────────────────────────────
            import re
            narrative_str = parsed.get("narrative", "")
            found_dollars = re.findall(r"\$([0-9,]+(?:\.[0-9]{2})?)", narrative_str)
            breached = False
            for d in found_dollars:
                val = float(d.replace(",", ""))
                if val > baseline_mrr + 1.0:
                    breached = True
                    break

            if breached and attempt < max_retries - 1:
                print(f"🛡️ [Sanitizer Triggered] Found dollar figure exceeding baseline limit ${baseline_mrr:,.0f} in narrative. Triggering 1-shot clean re-generation...")
                prompt += f"\n\nALERT: Your previous attempt contained a dollar figure exceeding ${baseline_mrr:,.0f}. You MUST re-synthesize without mentioning any number above ${baseline_mrr:,.0f}."
                continue

            return {
                "narrative": parsed.get("narrative", raw_text),
                "recommended_action": parsed.get("recommended_action", "Review change with team."),
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.0)
                continue
            print(f"[warning] DeepSeek LLM synthesis fallback triggered for {classification['event_id']}: {e}")

    if classification.get("validated"):
        return {
            "narrative": f"On date of change, {classification['actor']} made an undocumented {classification['node_type']} change on {classification['model_id']}. This change went unreviewed and directly caused a downstream incident after an extended detection lag.",
            "recommended_action": f"Review threshold and transformation configuration on {classification['model_id']} and add automated assertions.",
        }
    else:
        return {
            "narrative": f"On date of change, {classification['actor']} added an undocumented {classification['node_type']} to {classification['model_id']}. Superficially unreviewed, but no historical incidents have been traced to this change.",
            "recommended_action": "No immediate remediation required; flag for routine documentation cleanup.",
        }


def process_single_event(eid: str) -> Dict[str, Any]:
    time.sleep(0.1)  # Stagger requests to avoid 503 rate-limit spikes
    c = classify_pattern(eid)
    narrative_res = generate_finding_narrative(c)
    routed_info = resolve_dataset_routed_owner_info(c["model_id"])
    routed_team = routed_info["routed_to_team"]
    gov = resolve_dataset_governance_multiplier(c["model_id"])
    multiplier = gov["multiplier"]
    tag_source = gov["tag_source"]

    # E2.2 Final step severity escalation based on governance multiplier
    final_severity = c["severity"]
    if c["severity"] == "medium" and multiplier >= 1.5:
        final_severity = "high"
    elif c["severity"] == "low" and multiplier >= 1.5:
        final_severity = "medium"

    upsert_sql = """
        INSERT INTO findings (
            model_id,
            related_event_id,
            severity,
            validated,
            evidence_scope,
            routed_to_team,
            severity_multiplier,
            tag_source,
            narrative,
            recommended_action,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
        ON CONFLICT DO NOTHING
        RETURNING finding_id, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT finding_id FROM findings WHERE related_event_id = %s;", (eid,))
            existing = cur.fetchone()

            if existing:
                update_sql = """
                    UPDATE findings SET
                        severity = %s,
                        validated = %s,
                        evidence_scope = %s,
                        routed_to_team = %s,
                        severity_multiplier = %s,
                        tag_source = %s,
                        narrative = %s,
                        recommended_action = %s
                    WHERE related_event_id = %s
                    RETURNING finding_id, created_at;
                """
                cur.execute(update_sql, (
                    final_severity,
                    c["validated"],
                    c["scope_key"],
                    routed_team,
                    multiplier,
                    tag_source,
                    narrative_res["narrative"],
                    narrative_res["recommended_action"],
                    eid,
                ))
                row = cur.fetchone()
            else:
                cur.execute(upsert_sql, (
                    c["model_id"],
                    eid,
                    final_severity,
                    c["validated"],
                    c["scope_key"],
                    routed_team,
                    multiplier,
                    tag_source,
                    narrative_res["narrative"],
                    narrative_res["recommended_action"],
                ))
                row = cur.fetchone()

            if not row:
                cur.execute("SELECT finding_id FROM findings WHERE related_event_id = %s;", (eid,))
                row = cur.fetchone()
        conn.commit()

    fid = str(row["finding_id"])

    # B2.2 Ledger Event 1: finding_created
    append_to_ledger(
        event_type="finding_created",
        finding_id=fid,
        payload={
            "model_id": c["model_id"],
            "related_event_id": eid,
            "pattern_type": c["pattern_type"],
            "actor": c["actor"],
            "evidence_scope": c["scope_key"],
            "routed_to_team": routed_team,
            "severity_multiplier": multiplier,
            "tag_source": tag_source,
            "governance_tags": gov["tags_found"],
            "lineage_retrieved_via": "datahub-agent-context (get_lineage)",
            "narrative": narrative_res["narrative"],
            "recommended_action": narrative_res["recommended_action"],
        }
    )

    # E1 Ledger Event 2: ownership_routed
    append_to_ledger(
        event_type="ownership_routed",
        finding_id=fid,
        payload={
            "model_id": c["model_id"],
            "routed_to_team": routed_team,
            "priority_rule_matched": routed_info["priority_rule_matched"],
        }
    )

    # E2 Ledger Event 3: severity_tag_adjusted
    append_to_ledger(
        event_type="severity_tag_adjusted",
        finding_id=fid,
        payload={
            "model_id": c["model_id"],
            "base_severity": c["severity"],
            "final_severity": final_severity,
            "severity_multiplier": multiplier,
            "governance_tags": gov["tags_found"],
            "tag_source": tag_source,
        }
    )

    return {"finding_id": fid, "model_id": c["model_id"], "severity": final_severity, "narrative": narrative_res["narrative"], "recommended_action": narrative_res["recommended_action"]}


def populate_findings(max_workers: int = 2) -> List[Dict[str, Any]]:
    """
    Step 7.2: Evaluates all lineage events in PostgreSQL, runs correlation classification,
    synthesizes narrative & action via DeepSeek v4 Flash in parallel (2 workers),
    applies governance tag multipliers, and populates findings table.
    """
    events_query = "SELECT event_id FROM lineage_events ORDER BY event_timestamp;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(events_query)
            rows = cur.fetchall()

    event_ids = [str(r["event_id"]) for r in rows]

    print(f"\n=======================================================")
    print(f"   PARALLEL FINDINGS SYNTHESIS (Workers={max_workers})")
    print(f"=======================================================")
    print(f"Synthesizing narratives for {len(event_ids)} events across {max_workers} worker threads...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_single_event, event_ids))

    return results


def verify_findings_table() -> None:
    """
    Step 7.3 Verification helper.
    """
    query = """
        SELECT
            f.finding_id,
            f.model_id,
            f.severity,
            f.validated,
            f.evidence_scope,
            f.routed_to_team,
            f.severity_multiplier,
            f.tag_source,
            f.narrative,
            f.recommended_action,
            f.status
        FROM findings f
        ORDER BY f.created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    print(f"\n=======================================================")
    print(f"   FINDINGS TABLE INSPECTION ({len(rows)} RECORD(S) STORED)")
    print(f"=======================================================")

    for r in rows:
        print(f"► Finding ID:  {r['finding_id']}")
        print(f"  Model URN:   {r['model_id']}")
        print(f"  Severity:    {r['severity'].upper()} (Validated={r['validated']})")
        print(f"  Scope:       {r['evidence_scope']}")
        print(f"  Routed To:   {r['routed_to_team']}")
        print(f"  Tag Source:  {r['tag_source']} (Mult: {r['severity_multiplier']}x)")
        print(f"  Narrative:   {r['narrative']}")
        print(f"  Action:      {r['recommended_action']}")
        print("-------------------------------------------------------")


if __name__ == "__main__":
    populate_findings()
    verify_findings_table()
