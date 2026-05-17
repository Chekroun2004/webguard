"""
TechnologiesScanner — detects technology/version disclosure via HTTP headers.

Flags: Server header with version string (medium), without version (low),
and disclosure headers like X-Powered-By, X-Aspnet-Version.
"""
from __future__ import annotations

import re

from app.scanners.base import BaseScanner, Finding

VERSION_RE = re.compile(r"[\d.]+")

DISCLOSURE_HEADERS = [
    "X-Powered-By",
    "X-Aspnet-Version",
    "X-Aspnetmvc-Version",
    "X-Generator",
    "X-Drupal-Cache",
    "X-Runtime",
    "X-Version",
]


class TechnologiesScanner(BaseScanner):
    async def scan(self, url: str, config: dict) -> list[Finding]:
        response = await self._fetch(url)
        headers: dict[str, str] = {
            k.title(): v for k, v in response["headers"].items()
        }
        findings: list[Finding] = []

        server = headers.get("Server", "")
        if server:
            if VERSION_RE.search(server):
                findings.append(
                    Finding(
                        name="Server Version Disclosure",
                        severity="medium",
                        description=(
                            "The Server header reveals the software version, "
                            "which can help attackers fingerprint the server."
                        ),
                        recommendation="Configure the server to omit version information.",
                        evidence=server,
                    )
                )
            else:
                findings.append(
                    Finding(
                        name="Server Version Disclosure",
                        severity="low",
                        description="The Server header discloses the server software name.",
                        recommendation="Consider removing or masking the Server header.",
                        evidence=server,
                    )
                )

        for header in DISCLOSURE_HEADERS:
            value = headers.get(header, "")
            if value:
                findings.append(
                    Finding(
                        name="Technology Disclosure",
                        severity="low",
                        description=(
                            f"The '{header}' header discloses technology information."
                        ),
                        recommendation=f"Remove or mask the '{header}' header.",
                        evidence=f"{header}: {value}",
                    )
                )

        return findings
