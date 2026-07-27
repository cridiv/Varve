"""
Varve Slack Pager Service

Sends a formatted risk finding alert to a Slack channel via Webhook URL.
No SDK required — just a plain HTTP POST with a JSON body.

Configuration (via environment variables in service/.env):
  SLACK_WEBHOOK_URL   Incoming Webhook URL from Slack App configuration.
  FRONTEND_BASE_URL   Base URL of the Varve frontend (default: http://localhost:3000).
"""

import urllib.request
import json
from typing import Dict, Any, Optional

import sys, os
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from config.config import SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN, FRONTEND_BASE_URL


# ---------------------------------------------------------------------------
# Severity → Slack emoji & color
# ---------------------------------------------------------------------------

_SEVERITY_META = {
    "high":   {"emoji": "🔴", "color": "#E53E3E"},
    "medium": {"emoji": "🟠", "color": "#DD6B20"},
    "low":    {"emoji": "🟡", "color": "#D69E2E"},
}


def _build_blocks(
    *,
    model_name: str,
    severity: str,
    narrative: str,
    recommended_action: str,
    routed_to_team: Optional[str],
    finding_url: str,
    detection_lag_days: Optional[int],
    evidence_scope: str,
) -> list:
    """Builds a Slack Block Kit message body for a Varve risk finding."""
    sev = severity.lower()
    meta = _SEVERITY_META.get(sev, {"emoji": "⚪", "color": "#718096"})
    emoji = meta["emoji"]

    # Narrative trimmed to 280 chars so the message stays compact
    narrative_snippet = narrative[:280].rstrip() + ("…" if len(narrative) > 280 else "")

    lag_text = f"{detection_lag_days}d avg detection lag" if detection_lag_days is not None else "No historical precedent yet"
    owner_text = routed_to_team if routed_to_team else "Unassigned"

    blocks = [
        # ── Header bar ────────────────────────────────────────────────
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Varve Risk Alert — {model_name.upper()}",
                "emoji": True,
            },
        },
        # ── Severity / scope / lag metadata ───────────────────────────
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity*\n`{severity.upper()}`",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Evidence Scope*\n`{evidence_scope}`",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Routed To*\n{owner_text}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Historical Lag*\n{lag_text}",
                },
            ],
        },
        {"type": "divider"},
        # ── Narrative snippet ──────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Finding*\n{narrative_snippet}",
            },
        },
        # ── Recommended action ─────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action*\n{recommended_action}",
            },
        },
        {"type": "divider"},
        # ── CTA button linking back to the finding ─────────────────────
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in Varve →", "emoji": True},
                    "url": finding_url,
                    "style": "primary",
                    "action_id": "open_finding",
                }
            ],
        },
        # ── Footer context ─────────────────────────────────────────────
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Sent by Varve AI · <{FRONTEND_BASE_URL}|Open Dashboard>_",
                }
            ],
        },
    ]
    return blocks


def send_finding_alert(finding: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST a formatted Slack Block Kit alert for a single Varve risk finding.

    `finding` dict must contain at minimum:
        finding_id, model_name, severity, narrative,
        recommended_action, evidence_scope

    Optional fields:
        routed_to_team, detection_lag_days

    Returns a result dict with `ok`, `status`, and `error` keys.

    Delivery priority:
      1. SLACK_WEBHOOK_URL  (Incoming Webhook — preferred for v1)
      2. Slack Web API chat.postMessage via SLACK_BOT_TOKEN + channel kwarg
    """
    finding_id = str(finding.get("finding_id", ""))
    model_name = finding.get("model_name") or finding.get("model_id", "Unknown Model")
    severity = finding.get("severity", "medium")
    narrative = finding.get("narrative", "")
    recommended_action = finding.get("recommended_action", "")
    routed_to_team = finding.get("routed_to_team")
    detection_lag_days = finding.get("detection_lag_days") or finding.get("avg_lag_days")
    evidence_scope = finding.get("evidence_scope", "org_wide")

    finding_url = f"{FRONTEND_BASE_URL.rstrip('/')}/findings/{finding_id}"

    blocks = _build_blocks(
        model_name=model_name,
        severity=severity,
        narrative=narrative,
        recommended_action=recommended_action,
        routed_to_team=routed_to_team,
        finding_url=finding_url,
        detection_lag_days=detection_lag_days,
        evidence_scope=evidence_scope,
    )

    payload = {
        "text": f"[Varve] {severity.upper()} risk finding on *{model_name}* — review immediately.",
        "blocks": blocks,
    }

    # ── Attempt 1: Incoming Webhook ────────────────────────────────────────
    webhook_url = SLACK_WEBHOOK_URL
    if webhook_url:
        return _post_webhook(webhook_url, payload)

    # ── Attempt 2: Bot Token + chat.postMessage ────────────────────────────
    if SLACK_BOT_TOKEN:
        channel = finding.get("slack_channel", "#data-incidents")
        return _post_bot_api(SLACK_BOT_TOKEN, channel, payload)

    return {
        "ok": False,
        "status": None,
        "error": "No Slack credentials configured. Set SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN in service/.env.",
    }


def _post_webhook(webhook_url: str, payload: dict) -> Dict[str, Any]:
    """POST payload to a Slack Incoming Webhook URL."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            return {"ok": text == "ok" or resp.status == 200, "status": resp.status, "error": None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode("utf-8")}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}


def _post_bot_api(token: str, channel: str, payload: dict) -> Dict[str, Any]:
    """POST payload via Slack Web API chat.postMessage using a Bot token."""
    api_payload = {
        "channel": channel,
        "text": payload.get("text", ""),
        "blocks": payload.get("blocks", []),
    }
    body = json.dumps(api_payload).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"ok": result.get("ok", False), "status": resp.status, "error": result.get("error")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode("utf-8")}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}
