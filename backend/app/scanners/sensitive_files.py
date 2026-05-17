"""
SensitiveFilesScanner — probes for commonly exposed sensitive paths.

Flags any path that returns HTTP 200. 403/404 are not flagged.
"""

from __future__ import annotations

import httpx

from app.scanners.base import BaseScanner, Finding

SENSITIVE_PATHS = [
    "/.git/HEAD",
    "/.env",
    "/.env.local",
    "/.env.backup",
    "/config.php",
    "/wp-config.php",
    "/web.config",
    "/.htaccess",
    "/phpinfo.php",
    "/server-status",
    "/backup.zip",
    "/backup.tar.gz",
    "/db.sql",
    "/database.sql",
    "/admin/",
    "/phpmyadmin/",
]


class SensitiveFilesScanner(BaseScanner):
    async def _check_path(self, url: str) -> int:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
            try:
                resp = await client.get(url)
                return resp.status_code
            except OSError:
                return 0

    async def scan(self, url: str, config: dict) -> list[Finding]:
        base = url.rstrip("/")
        findings: list[Finding] = []

        for path in SENSITIVE_PATHS:
            target = base + path
            status = await self._check_path(target)
            if status == 200:
                findings.append(
                    Finding(
                        name="Exposed Sensitive File",
                        severity="high",
                        description=f"The path '{path}' is publicly accessible.",
                        recommendation=(
                            "Restrict access to sensitive files via server configuration."
                        ),
                        evidence=target,
                    )
                )

        return findings
