"""
Webhook sender — fans out scan-complete notifications to user-configured Slack/Discord endpoints.

Fire-and-forget semantics: any HTTP error is logged but never propagates. A
broken webhook must never fail the scan task or block other notifications.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.scan import Scan, Vulnerability
from app.db.models.webhook import Webhook
from app.repositories.webhook import list_active_webhooks_for_user

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

_SEVERITY_COLOR_HEX = {
    "critical": 0x991B1B,
    "high": 0xDC2626,
    "medium": 0xF59E0B,
    "low": 0x3B82F6,
    "info": 0x6B7280,
}


def _summarize(findings: list[Vulnerability]) -> dict[str, int]:
    counts = {s: 0 for s in _SEVERITY_ORDER}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1
    return {"total": len(findings), **counts}


def _scan_url(scan: Scan) -> str:
    return f"{settings.frontend_url.rstrip('/')}/scans/{scan.id}"


def _top_severity(findings: list[Vulnerability]) -> str:
    for sev in _SEVERITY_ORDER:
        if any(f.severity == sev for f in findings):
            return sev
    return "info"


def build_slack_payload(scan: Scan, findings: list[Vulnerability]) -> dict[str, Any]:
    summary = _summarize(findings)
    text = f"WebGuard scan terminé — {summary['total']} vulnérabilité(s) sur {scan.url}"
    fields = [
        {"type": "mrkdwn", "text": f"*Critical:* {summary['critical']}"},
        {"type": "mrkdwn", "text": f"*High:* {summary['high']}"},
        {"type": "mrkdwn", "text": f"*Medium:* {summary['medium']}"},
        {"type": "mrkdwn", "text": f"*Low:* {summary['low']}"},
    ]
    return {
        "text": text,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "WebGuard scan terminé"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Cible:* {scan.url}"},
            },
            {"type": "section", "fields": fields},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Voir le rapport"},
                        "url": _scan_url(scan),
                    }
                ],
            },
        ],
    }


def build_discord_payload(scan: Scan, findings: list[Vulnerability]) -> dict[str, Any]:
    summary = _summarize(findings)
    color = (
        _SEVERITY_COLOR_HEX[_top_severity(findings)] if findings else _SEVERITY_COLOR_HEX["info"]
    )
    embed = {
        "title": "WebGuard scan terminé",
        "url": _scan_url(scan),
        "description": f"**Cible:** {scan.url}\n**Total:** {summary['total']} vulnérabilité(s)",
        "color": color,
        "fields": [
            {"name": "Critical", "value": str(summary["critical"]), "inline": True},
            {"name": "High", "value": str(summary["high"]), "inline": True},
            {"name": "Medium", "value": str(summary["medium"]), "inline": True},
            {"name": "Low", "value": str(summary["low"]), "inline": True},
        ],
    }
    return {"content": None, "embeds": [embed]}


def build_payload(provider: str, scan: Scan, findings: list[Vulnerability]) -> dict[str, Any]:
    if provider == "slack":
        return build_slack_payload(scan, findings)
    if provider == "discord":
        return build_discord_payload(scan, findings)
    raise ValueError(f"Unknown webhook provider: {provider}")


async def _post(url: str, payload: dict[str, Any]) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Webhook POST to %s failed: %s", url, exc)
        return False


async def send_to_webhook(webhook: Webhook, scan: Scan, findings: list[Vulnerability]) -> bool:
    try:
        payload = build_payload(webhook.provider, scan, findings)
    except ValueError as exc:
        logger.warning("Skipping webhook %s: %s", webhook.id, exc)
        return False
    return await _post(webhook.url, payload)


async def notify_scan_complete(
    db: AsyncSession, user_id: int, scan: Scan, findings: list[Vulnerability]
) -> int:
    """Send scan-complete notifications to all active webhooks for the user.

    Returns the number of webhooks that accepted the payload (HTTP 2xx).
    """
    webhooks = await list_active_webhooks_for_user(db, user_id)
    delivered = 0
    for webhook in webhooks:
        if await send_to_webhook(webhook, scan, findings):
            delivered += 1
    return delivered
