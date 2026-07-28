"""
Varve MCP Server — Model Context Protocol interface for Varve Risk Intelligence.

Exposes Varve's risk intelligence capabilities as MCP tools so any MCP-compatible
AI client (Claude Desktop, Cursor, custom agents) can query and act on ML risk data
directly — without opening the Varve web UI.

Transport: stdio (default) — run as a subprocess from any MCP client.
           HTTP/SSE     — pass --transport streamable-http for hosted mode.

Usage (stdio):
    python service/mcp_server.py

Claude Desktop config (~/.config/claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "varve": {
          "command": "python",
          "args": ["/absolute/path/to/varve/service/mcp_server.py"]
        }
      }
    }

HTTP mode (hosted):
    python service/mcp_server.py --transport streamable-http --port 8001
"""

import sys
import os
import json
from typing import Optional

# Make service/ importable regardless of where this file is invoked from
service_dir = os.path.dirname(os.path.abspath(__file__))
if service_dir not in sys.path:
    sys.path.insert(0, service_dir)

from fastmcp import FastMCP
from db.connection import get_db_connection
from services.ledger_service import verify_ledger_chain
from services.datahub_service import writeback_finding_to_datahub

# ---------------------------------------------------------------------------
# Server instantiation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Varve — ML Risk Intelligence",
    instructions=(
        "Varve is an AI-powered production ML risk triage engine built on DataHub. "
        "It reads DataHub's lineage graph layer-by-layer to surface hidden technical debt "
        "before it becomes a production incident. Use these tools to:\n"
        "  • get_risk_ranking   — see which models are most at risk right now\n"
        "  • get_finding_detail — deep-dive one finding with full lineage evidence\n"
        "  • get_actor_history  — investigate an engineer's cross-model impact history\n"
        "  • emit_risk_pattern  — write a validated risk pattern back to DataHub's graph\n"
        "  • verify_audit_chain — cryptographically verify every decision Varve has made\n"
        "  • get_org_stats      — summary stats across all tracked models\n"
        "All findings are evidence-tiered (org_wide / actor / industry_general) and every "
        "decision is SHA-256 hash-chained in an append-only audit ledger."
    ),
)

# ---------------------------------------------------------------------------
# Shared label maps (mirrors api/findings.py — kept in sync manually)
# ---------------------------------------------------------------------------

EVIDENCE_LABELS = {
    "model": "Backed by direct model incident history",
    "actor": "Backed by actor cross-model incident history",
    "org_wide": "Backed by company-wide pattern history",
    "industry_general": "Backed by published industry data (cold-start fallback)",
}

TAG_SOURCE_LABELS = {
    "datahub_native": "Verified DataHub Catalog Tag",
    "inferred": "Inferred from Schema (Heuristic Fallback)",
    "none": "Untagged",
}


# ---------------------------------------------------------------------------
# Tool 1 — get_risk_ranking
# ---------------------------------------------------------------------------

@mcp.tool()
def get_risk_ranking() -> list[dict]:
    """
    Returns Varve's current risk-ranked list of production ML model findings,
    ordered by severity (high first) then validation status.

    Each finding includes:
    - finding_id, model_name, severity (high/medium/low)
    - validated: whether backed by real org incident history
    - evidence_scope + evidence_label: how strong the evidence is
    - routed_to_team: DataHub-resolved owner responsible for the model
    - actor: engineer who made the upstream lineage change
    - detection_lag_days: days between the causal change and the historical incident
    - narrative: LLM-synthesised explanation of the risk
    - recommended_action: actionable remediation step
    - written_back: whether a risk pattern has been written back to DataHub

    Use this as your starting point to understand the current risk landscape.
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
            f.status,
            f.narrative,
            f.recommended_action,
            f.written_back_at,
            f.created_at,
            e.actor,
            e.node_type,
            e.event_timestamp,
            i.detected_at AS incident_detected_at
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        LEFT JOIN incidents i ON f.related_event_id = i.root_cause_event_id
        ORDER BY
            CASE WHEN f.severity = 'high' THEN 1 ELSE 2 END,
            f.validated DESC,
            f.created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]

    results = []
    for r in rows:
        urn_parts = r["model_id"].split(".")
        model_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]
        ev_scope = r.get("evidence_scope", "org_wide")
        ts = r.get("tag_source", "none")

        event_ts = r.get("event_timestamp")
        inc_ts = r.get("incident_detected_at")
        lag_days = (
            int(round((inc_ts - event_ts).total_seconds() / 86400.0))
            if (inc_ts and event_ts) else None
        )

        results.append({
            "finding_id": str(r["finding_id"]),
            "model_name": model_name,
            "model_id": r["model_id"],
            "severity": r["severity"],
            "validated": r["validated"],
            "evidence_scope": ev_scope,
            "evidence_label": EVIDENCE_LABELS.get(ev_scope, ev_scope),
            "routed_to_team": r.get("routed_to_team", "Unassigned"),
            "severity_multiplier": float(r.get("severity_multiplier") or 1.0),
            "tag_source_label": TAG_SOURCE_LABELS.get(ts, "Untagged"),
            "status": r["status"],
            "actor": r["actor"],
            "node_type": r["node_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r["event_timestamp"] else None,
            "detection_lag_days": lag_days,
            "narrative": r["narrative"],
            "recommended_action": r["recommended_action"],
            "written_back": r["written_back_at"] is not None,
        })

    return results


# ---------------------------------------------------------------------------
# Tool 2 — get_finding_detail
# ---------------------------------------------------------------------------

@mcp.tool()
def get_finding_detail(finding_id: str) -> dict:
    """
    Returns full details for one specific finding identified by its finding_id.

    Includes:
    - Complete finding metadata (severity, evidence tier, governance tags)
    - event_details: the exact upstream lineage change that triggered this finding
      (node_type, node_urn, actor, event_timestamp, documentation_present)
    - matched_incident: the historical incident this pattern was correlated against,
      including detection_lag_days and whether it was a cross-model incident
    - audit_summary: number of ledger entries recorded for this finding

    Use get_risk_ranking() first to obtain a finding_id, then call this tool
    to investigate a specific finding in depth.
    """
    finding_query = """
        SELECT
            f.finding_id, f.model_id, f.severity, f.validated, f.evidence_scope,
            f.routed_to_team, f.severity_multiplier, f.tag_source,
            f.narrative, f.recommended_action, f.status,
            f.written_back_at, f.created_at, f.related_event_id,
            e.node_type, e.node_urn, e.event_type, e.event_timestamp,
            e.actor, e.documentation_present
        FROM findings f
        JOIN lineage_events e ON f.related_event_id = e.event_id
        WHERE f.finding_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(finding_query, (finding_id,))
            row = cur.fetchone()

    if not row:
        return {"error": f"Finding '{finding_id}' not found."}

    finding = dict(row)

    # Matched incident
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT incident_id, model_id AS target_model_id,
                       detected_at, resolved_at, description, fix_summary
                FROM incidents
                WHERE root_cause_event_id = %s;
            """, (finding["related_event_id"],))
            incidents = [dict(r) for r in cur.fetchall()]

    matched_incident = None
    if incidents:
        inc = incidents[0]
        event_ts = finding["event_timestamp"]
        detected_ts = inc["detected_at"]
        lag = None
        if detected_ts and event_ts:
            lag = int(round((detected_ts - event_ts).total_seconds() / 86400.0))
        matched_incident = {
            "incident_id": str(inc["incident_id"]),
            "target_model_id": inc["target_model_id"],
            "detected_at": inc["detected_at"].isoformat() if inc["detected_at"] else None,
            "resolved_at": inc["resolved_at"].isoformat() if inc["resolved_at"] else None,
            "description": inc["description"],
            "fix_summary": inc["fix_summary"],
            "detection_lag_days": lag,
            "is_cross_model": inc["target_model_id"] != finding["model_id"],
        }

    # Audit ledger count for this finding
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM ledger WHERE finding_id = %s;",
                (finding_id,)
            )
            ledger_count = cur.fetchone()["n"]

    urn_parts = finding["model_id"].split(".")
    model_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else finding["model_id"]
    ev_scope = finding.get("evidence_scope", "org_wide")
    ts = finding.get("tag_source", "none")

    return {
        "finding_id": str(finding["finding_id"]),
        "model_name": model_name,
        "model_id": finding["model_id"],
        "severity": finding["severity"],
        "validated": finding["validated"],
        "evidence_scope": ev_scope,
        "evidence_label": EVIDENCE_LABELS.get(ev_scope, ev_scope),
        "routed_to_team": finding.get("routed_to_team", "Unassigned"),
        "severity_multiplier": float(finding.get("severity_multiplier") or 1.0),
        "tag_source_label": TAG_SOURCE_LABELS.get(ts, "Untagged"),
        "status": finding["status"],
        "narrative": finding["narrative"],
        "recommended_action": finding["recommended_action"],
        "written_back": finding["written_back_at"] is not None,
        "written_back_at": finding["written_back_at"].isoformat() if finding["written_back_at"] else None,
        "created_at": finding["created_at"].isoformat() if finding["created_at"] else None,
        "event_details": {
            "event_id": str(finding["related_event_id"]),
            "node_type": finding["node_type"],
            "node_urn": finding["node_urn"],
            "event_type": finding["event_type"],
            "event_timestamp": finding["event_timestamp"].isoformat() if finding["event_timestamp"] else None,
            "actor": finding["actor"],
            "documentation_present": finding["documentation_present"],
        },
        "matched_incident": matched_incident,
        "audit_ledger_entries": ledger_count,
    }


# ---------------------------------------------------------------------------
# Tool 3 — get_actor_history
# ---------------------------------------------------------------------------

@mcp.tool()
def get_actor_history(actor_name: str) -> dict:
    """
    Returns the cross-model lineage history for a specific engineer (actor).

    Solves "single-model blindness" — shows every upstream change the actor made
    across ALL models and whether any of those changes preceded production incidents
    (even on different models, weeks later).

    Returns:
    - identity_mapping: the DataHub corpuser URN resolved for this actor
    - total_events: total lineage changes authored across all models
    - events_with_incidents: how many of those changes are linked to real incidents
    - incident_rate_pct: percentage of their changes that preceded incidents
    - avg_detection_lag_days: average days between change and detected incident
    - events: full timeline of changes + linked incidents

    actor_name examples: "J. Alvarez", "K. Vance", "R. Chen", "M. Santos"
    """
    # Fetch all lineage events for this actor with linked incidents
    query = """
        SELECT
            e.event_id, e.model_id, e.node_type, e.event_type,
            e.event_timestamp, e.actor, e.actor_departed_within_90d,
            e.documentation_present,
            i.incident_id, i.model_id AS incident_model_id,
            i.detected_at, i.description, i.fix_summary,
            EXTRACT(EPOCH FROM (i.detected_at - e.event_timestamp)) / 86400.0 AS detection_lag_days
        FROM lineage_events e
        LEFT JOIN incidents i ON i.root_cause_event_id = e.event_id
        WHERE LOWER(e.actor) LIKE LOWER(%s)
        ORDER BY e.event_timestamp DESC;
    """
    search = f"%{actor_name}%"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (search,))
            rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return {
            "actor": actor_name,
            "error": f"No lineage events found for actor '{actor_name}'. "
                     "Try names like 'J. Alvarez', 'K. Vance', 'R. Chen', 'M. Santos'."
        }

    # Actor identity from actor_owner_mappings
    identity_mapping = {"datahub_owner_urn": "unresolved", "datahub_display_name": actor_name, "match_type": "none"}
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datahub_owner_urn, datahub_display_name, match_type "
                "FROM actor_owner_mappings WHERE LOWER(lineage_actor) LIKE LOWER(%s) LIMIT 1;",
                (search,)
            )
            mapping_row = cur.fetchone()
            if mapping_row:
                identity_mapping = dict(mapping_row)

    events_out = []
    for r in rows:
        urn_parts = r["model_id"].split(".")
        model_name = urn_parts[-1].replace(",PROD)", "") if urn_parts else r["model_id"]

        linked_incident = None
        if r.get("incident_id"):
            inc_urn = r.get("incident_model_id", "")
            inc_model_name = inc_urn.split(".")[-1].replace(",PROD)", "") if inc_urn else inc_urn
            lag = int(round(float(r["detection_lag_days"]))) if r.get("detection_lag_days") is not None else None
            linked_incident = {
                "incident_id": str(r["incident_id"]),
                "incident_model_name": inc_model_name,
                "incident_model_id": inc_urn,
                "detected_at": r["detected_at"].isoformat() if r.get("detected_at") else None,
                "description": r.get("description"),
                "fix_summary": r.get("fix_summary"),
                "detection_lag_days": lag,
            }

        events_out.append({
            "event_id": str(r["event_id"]),
            "model_name": model_name,
            "model_id": r["model_id"],
            "node_type": r["node_type"],
            "event_type": r["event_type"],
            "event_timestamp": r["event_timestamp"].isoformat() if r.get("event_timestamp") else None,
            "actor_departed_within_90d": bool(r.get("actor_departed_within_90d", False)),
            "documentation_present": bool(r.get("documentation_present", True)),
            "linked_incident": linked_incident,
        })

    events_with_incidents = sum(1 for e in events_out if e["linked_incident"])
    lags = [e["linked_incident"]["detection_lag_days"] for e in events_out if e["linked_incident"] and e["linked_incident"]["detection_lag_days"] is not None]
    avg_lag = int(round(sum(lags) / len(lags))) if lags else None
    incident_rate = round(100 * events_with_incidents / len(events_out)) if events_out else 0

    return {
        "actor": actor_name,
        "identity_mapping": identity_mapping,
        "total_events": len(events_out),
        "events_with_incidents": events_with_incidents,
        "incident_rate_pct": incident_rate,
        "avg_detection_lag_days": avg_lag,
        "events": events_out,
    }


# ---------------------------------------------------------------------------
# Tool 4 — emit_risk_pattern
# ---------------------------------------------------------------------------

@mcp.tool()
def emit_risk_pattern(finding_id: str) -> dict:
    """
    Writes Varve's risk assessment for a finding back to DataHub's graph as an
    InstitutionalMemory annotation on the upstream lineage dataset node.

    This is Varve's write-back path — turning read-only risk analysis into
    durable knowledge that lives in the DataHub catalog for future agents and
    engineers to find.

    The annotation includes:
    - A direct link to the Varve finding detail page
    - The full risk narrative and recommended action
    - The severity level

    Idempotent: calling this multiple times for the same finding_id is safe —
    Varve detects the existing ledger entry and skips duplicate emissions.

    Returns the DataHub dataset URN that was annotated and the audit ledger hash
    proving this write-back was recorded.

    Use get_risk_ranking() to find a finding_id to pass here.
    """
    try:
        result = writeback_finding_to_datahub(finding_id, force=False)
        return {
            "success": True,
            "finding_id": finding_id,
            "dataset_urn": result.get("dataset_urn"),
            "status": result.get("status"),
            "already_written_back": result.get("already_written_back", False),
            "audit_ledger_hash": result.get("this_hash"),
            "message": (
                "Risk pattern already written to DataHub (idempotent — no duplicate emitted)."
                if result.get("already_written_back")
                else f"Risk pattern written to DataHub on dataset: {result.get('dataset_urn')}"
            ),
        }
    except Exception as e:
        return {
            "success": False,
            "finding_id": finding_id,
            "error": str(e),
            "message": "Write-back failed. Ensure Varve backend has DataHub GMS access configured.",
        }


# ---------------------------------------------------------------------------
# Tool 5 — verify_audit_chain
# ---------------------------------------------------------------------------

@mcp.tool()
def verify_audit_chain() -> dict:
    """
    Cryptographically verifies Varve's entire SHA-256 audit ledger chain.

    Every decision Varve makes (finding created, ownership routed, severity adjusted,
    writeback emitted, incident confirmed) is appended to an append-only hash chain:

        H_n = SHA256(H_{n-1} || event_type || finding_id || payload || timestamp)

    This tool re-computes every hash in memory from scratch (zero caching) and
    confirms whether the chain is intact. A single altered byte in any historical
    decision record will immediately break the chain and identify the corrupted row.

    Returns:
    - verified: True if all entries are intact
    - entries_checked: total number of decision blocks verified
    - message: human-readable result summary
    - failed_row_index / failed_ledger_id: populated only if verification fails
    """
    try:
        res = verify_ledger_chain()
        if res.get("valid"):
            return {
                "verified": True,
                "entries_checked": res.get("total_verified", 0),
                "message": f"✓ All {res.get('total_verified', 0)} decision blocks verified. Zero tampering detected.",
            }
        else:
            return {
                "verified": False,
                "entries_checked": res.get("total_verified", 0),
                "failed_row_index": res.get("failed_row_index"),
                "failed_ledger_id": res.get("failed_ledger_id"),
                "error": res.get("error"),
                "message": "⚠ Ledger chain verification FAILED — a decision record may have been tampered with.",
            }
    except Exception as e:
        return {
            "verified": False,
            "entries_checked": 0,
            "error": str(e),
            "message": "Ledger verification encountered an error.",
        }


# ---------------------------------------------------------------------------
# Tool 6 — get_org_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_org_stats() -> dict:
    """
    Returns organisation-wide summary statistics across all Varve-tracked models.

    Useful for getting a quick health pulse before diving into individual findings:
    - Total findings tracked and their severity breakdown
    - % that are org-validated (backed by real incident history vs industry fallback)
    - Total confirmed historical incidents in the database
    - Audit ledger depth (total decision blocks recorded)
    - DataHub writebacks completed
    - Pending candidate incidents awaiting human review
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT severity, COUNT(*) AS n FROM findings GROUP BY severity;")
            severity_rows = {r["severity"]: r["n"] for r in cur.fetchall()}

            cur.execute("SELECT COUNT(*) AS n FROM findings WHERE validated = TRUE;")
            validated_count = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM findings;")
            total_findings = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM incidents;")
            total_incidents = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM ledger;")
            ledger_depth = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM findings WHERE written_back_at IS NOT NULL;")
            writebacks = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM candidate_incidents WHERE status = 'pending';")
            pending_candidates = cur.fetchone()["n"]

    validated_pct = round(100 * validated_count / total_findings) if total_findings else 0

    return {
        "total_findings": total_findings,
        "severity_breakdown": {
            "high": severity_rows.get("high", 0),
            "medium": severity_rows.get("medium", 0),
            "low": severity_rows.get("low", 0),
        },
        "validated_findings": validated_count,
        "validated_pct": validated_pct,
        "total_confirmed_incidents": total_incidents,
        "audit_ledger_depth": ledger_depth,
        "datahub_writebacks_completed": writebacks,
        "pending_candidate_incidents": pending_candidates,
        "summary": (
            f"{total_findings} findings tracked — {severity_rows.get('high', 0)} high-severity. "
            f"{validated_pct}% org-validated. "
            f"{ledger_depth} audit blocks. "
            f"{pending_candidates} candidate(s) awaiting human review."
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
