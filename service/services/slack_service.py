"""
Varve Slack Pager Service — delivery layer only.

Responsibility: take a finding dict, build the Block Kit payload via
slack_payload_builder, and POST it to Slack.  Zero payload-shape knowledge
lives here; all of that is in slack_payload_builder.py.

Delivery priority:
  1. SLACK_WEBHOOK_URL  (Incoming Webhook — preferred for v1, no scopes needed)
  2. SLACK_BOT_TOKEN + chat.postMessage  (fallback; channel overrideable per-call)

No SDK required — plain urllib.request throughout.
"""

import urllib.request
import json
from typing import Dict, Any

import sys, os
service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_dir not in sys.path:
    sys.path.append(service_dir)

from config.config import SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN, FRONTEND_BASE_URL
from services.slack_payload_builder import build_slack_payload


def send_finding_alert(finding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a formatted Slack Block Kit alert for a single Varve risk finding.

    Required keys in `finding`:
        finding_id, severity, narrative, recommended_action, evidence_scope
        model_id  (or model_name)

    Optional keys:
        routed_to_team, avg_detection_lag_days, detection_lag_days,
        slack_channel  (used only for bot-token path, default: #data-incidents)

    Returns:
        { "ok": bool, "status": int | None, "error": str | None }
    """
    finding_id  = str(finding.get("finding_id", ""))
    finding_url = f"{FRONTEND_BASE_URL.rstrip('/')}/findings/{finding_id}"

    payload = build_slack_payload(finding, finding_url)

    # ── Priority 1: Incoming Webhook ──────────────────────────────────────
    if SLACK_WEBHOOK_URL:
        return _post_webhook(SLACK_WEBHOOK_URL, payload)

    # ── Priority 2: Bot token + chat.postMessage ──────────────────────────
    if SLACK_BOT_TOKEN:
        channel = finding.get("slack_channel", "#data-incidents")
        return _post_bot_api(SLACK_BOT_TOKEN, channel, payload)

    return {
        "ok":     False,
        "status": None,
        "error":  (
            "No Slack credentials configured. "
            "Set SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN in service/.env."
        ),
    }


# ── Transport helpers ──────────────────────────────────────────────────────────

def _post_webhook(webhook_url: str, payload: dict) -> Dict[str, Any]:
    """POST a Block Kit payload to a Slack Incoming Webhook URL."""
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            # Webhooks return the literal string "ok" on success
            return {
                "ok":     text.strip() == "ok" or resp.status == 200,
                "status": resp.status,
                "error":  None,
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code,  "error": e.read().decode("utf-8")}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}


def _post_bot_api(token: str, channel: str, payload: dict) -> Dict[str, Any]:
    """POST via Slack Web API chat.postMessage using a Bot User OAuth Token."""
    api_payload = {
        "channel": channel,
        "text":    payload.get("text", ""),
        "blocks":  payload.get("blocks", []),
    }
    body = json.dumps(api_payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "ok":     result.get("ok", False),
                "status": resp.status,
                "error":  result.get("error"),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code,  "error": e.read().decode("utf-8")}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}
