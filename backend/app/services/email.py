"""
Email service — sends a notification when a scan completes.

Uses aiosmtplib so it works inside async Celery tasks. All send failures are
swallowed and logged — a failed email must NEVER fail the scan task.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.db.models.scan import Scan, Vulnerability

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def _build_summary(findings: list[Vulnerability]) -> dict[str, int]:
    counts = {s: 0 for s in _SEVERITY_ORDER}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1
    return {"total": len(findings), **counts}


def _top_findings(findings: list[Vulnerability], limit: int = 5) -> list[Vulnerability]:
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_ORDER.index(f.severity) if f.severity in _SEVERITY_ORDER else 99),
    )[:limit]


async def send_scan_complete_email(
    user_email: str,
    user_name: str | None,
    scan: Scan,
    findings: list[Vulnerability],
) -> bool:
    """Send a scan-complete notification email. Returns True on success."""
    if not settings.email_notifications_enabled:
        return False

    summary = _build_summary(findings)
    template = _jinja_env.get_template("email_scan_complete.html")
    html_body = template.render(
        scan=scan,
        user_name=user_name,
        summary=summary,
        top_findings=_top_findings(findings),
        scan_url=f"{settings.frontend_url.rstrip('/')}/scans/{scan.id}",
    )

    subject = f"[WebGuard] Scan terminé — {summary['total']} vulnérabilité(s) sur {scan.url}"

    message = EmailMessage()
    message["From"] = settings.from_email
    message["To"] = user_email
    message["Subject"] = subject
    message.set_content(
        f"Votre scan de {scan.url} est terminé. "
        f"{summary['total']} vulnérabilité(s) détectée(s). "
        f"Voir le rapport : {settings.frontend_url.rstrip('/')}/scans/{scan.id}"
    )
    message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=settings.smtp_use_tls,
            timeout=10,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to send scan-complete email: %s", exc)
        return False
