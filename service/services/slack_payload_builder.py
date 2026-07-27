"""
Slack notification payload builder for Varve.

Replaces the thin, raw-URN message with a properly structured Block Kit
payload: friendly model name, severity as a color-coded header, evidence
scope explained in plain language, the actual narrative snippet, and a
direct link back to the finding on Varve itself.

Call build_slack_payload(finding, finding_url) and POST the result as JSON
to your SLACK_WEBHOOK_URL.
"""

import sys, os
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from config import config


SEVERITY_EMOJI = {
    "high":   "🔴",
    "medium": "🟠",
    "low":    "🟢",
}

EVIDENCE_SCOPE_LABEL = {
    "org_wide":        "Backed by this organization's own confirmed incidents",
    "actor":           "Backed by this actor's confirmed incident history",
    "model":           "Backed by this specific model's incident history",
    "industry_general":"Backed by an industry baseline — no org history yet",
}


def friendly_model_name(urn_or_name: str) -> str:
    """
    Extract a short, readable name from a DataHub URN, or pass through
    if it's already a friendly name. Never show a raw URN in a Slack message.

    e.g. "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)"
    → "customers"
    """
    if not urn_or_name.startswith("urn:li:dataset:"):
        return urn_or_name
    try:
        inner = urn_or_name.split(",")[1]   # "b2fd91.order_entry_db.order_entry.customers"
        return inner.split(".")[-1]
    except (IndexError, AttributeError):
        return urn_or_name


def format_lag(avg_detection_lag_days: float) -> str:
    """
    Defensive formatting — if a negative value ever reaches this function,
    surface it as an explicit anomaly rather than silently displaying a
    nonsensical negative duration. This should never trigger once the
    underlying date-subtraction bug is fixed, but fail loudly, not quietly,
    if it ever does.
    """
    if avg_detection_lag_days < 0:
        return f"⚠️ invalid ({avg_detection_lag_days:.0f}d) — check calculation"
    if avg_detection_lag_days < 1:
        return "Same day (<1 day)"
    return f"{avg_detection_lag_days:.0f} days"


def build_slack_payload(finding: dict, finding_url: str) -> dict:
    """
    Build a fully structured Slack Block Kit payload for a Varve risk finding.

    Args:
        finding:     The finding record dict. Expected keys:
                       model_id / model_name, severity, evidence_scope,
                       routed_to_team, narrative, recommended_action,
                       avg_detection_lag_days (float).
        finding_url: Full URL to this finding on Varve, e.g.
                     f"{config.FRONTEND_BASE_URL}/findings/{finding['finding_id']}"

    Returns:
        A dict ready to be JSON-encoded and POSTed to SLACK_WEBHOOK_URL.
    """
    model_name = friendly_model_name(
        finding.get("model_id") or finding.get("model_name") or "unknown model"
    )
    severity      = finding.get("severity", "unknown").lower()
    emoji         = SEVERITY_EMOJI.get(severity, "⚪")
    evidence_scope = finding.get("evidence_scope", "unknown")
    scope_label   = EVIDENCE_SCOPE_LABEL.get(evidence_scope, evidence_scope)
    lag_raw       = finding.get("avg_detection_lag_days") or finding.get("detection_lag_days") or 0
    lag_text      = format_lag(float(lag_raw))
    owner         = finding.get("routed_to_team") or "No owner resolved"
    narrative     = finding.get("narrative", "").strip()
    recommended_action = finding.get("recommended_action", "").strip()

    return {
        # Fallback text shown in notifications / accessibility clients
        "text": f"{emoji} {severity.upper()} risk confirmed on *{model_name}* — review immediately.",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {severity.upper()} risk confirmed — {model_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Evidence*\n{scope_label}"},
                    {"type": "mrkdwn", "text": f"*Avg. detection lag*\n{lag_text}"},
                    {"type": "mrkdwn", "text": f"*Routed to*\n{owner}"},
                    {"type": "mrkdwn", "text": f"*Status*\nJust confirmed by review"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*What happened*\n{narrative}" if narrative else "_No narrative available._",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommended action*\n{recommended_action}" if recommended_action else "_No recommendation available._",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View finding on Varve →",
                            "emoji": True,
                        },
                        "url": finding_url,
                        "style": "danger" if severity == "high" else "primary",
                    }
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Sent by Varve · every claim above is independently verifiable via the audit ledger.",
                    }
                ],
            },
        ],
    }
