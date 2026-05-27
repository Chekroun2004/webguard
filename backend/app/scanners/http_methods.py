"""
HttpMethodsScanner — checks for dangerous HTTP methods via OPTIONS.

Flags: TRACE (high), PUT / DELETE / CONNECT / PATCH on unusual paths (medium).
"""

from __future__ import annotations

import httpx

from app.scanners.base import BaseScanner, Finding

DANGEROUS_METHODS: dict[str, str] = {
    "TRACE": "high",
    "PUT": "medium",
    "DELETE": "medium",
    "CONNECT": "medium",
}


class HttpMethodsScanner(BaseScanner):
    async def _options(self, url: str, cookies: dict[str, str] | None = None) -> dict:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10, cookies=cookies or {}
        ) as client:
            try:
                resp = await client.options(url)
                allow = resp.headers.get("allow", "")
                return {"status": resp.status_code, "allow": allow}
            except OSError:
                return {"status": 0, "allow": ""}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        result = await self._options(url, cookies=config.get("cookies"))
        findings: list[Finding] = []

        if result["status"] not in (200, 204):
            return findings

        allowed = {m.strip().upper() for m in result["allow"].split(",")}

        for method, severity in DANGEROUS_METHODS.items():
            if method in allowed:
                findings.append(
                    Finding(
                        name="Dangerous HTTP Method Enabled",
                        severity=severity,
                        description=f"The HTTP method {method} is enabled on the server.",
                        recommendation=f"Disable the {method} method unless explicitly required.",
                        evidence=f"Allow: {result['allow']} — {method} is enabled",
                    )
                )

        return findings
