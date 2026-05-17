"""
CookiesScanner — checks Set-Cookie header security attributes.

Flags cookies missing: Secure, HttpOnly, SameSite.
Also flags SameSite=None without Secure (allows cross-site sending over HTTP).
"""
from __future__ import annotations

import httpx

from app.scanners.base import BaseScanner, Finding


class CookiesScanner(BaseScanner):
    async def _fetch(self, url: str) -> dict:  # type: ignore[override]
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url)
            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "set_cookies": resp.headers.get_list("set-cookie"),
                "body": resp.text,
            }

    async def scan(self, url: str, config: dict) -> list[Finding]:
        response = await self._fetch(url)
        findings: list[Finding] = []
        for raw in response.get("set_cookies", []):
            findings.extend(self._check_cookie(raw))
        return findings

    def _check_cookie(self, raw: str) -> list[Finding]:
        findings: list[Finding] = []
        parts = [p.strip() for p in raw.split(";")]
        flags = {p.split("=")[0].strip().lower() for p in parts[1:]}
        samesite_val = ""
        for p in parts[1:]:
            kv = p.split("=", 1)
            if kv[0].strip().lower() == "samesite" and len(kv) == 2:
                samesite_val = kv[1].strip().lower()

        name = parts[0].split("=")[0].strip()

        if "secure" not in flags:
            findings.append(
                Finding(
                    name="Cookie Missing Secure Flag",
                    severity="medium",
                    description=f"Cookie '{name}' is missing the Secure flag.",
                    recommendation="Add the Secure flag to prevent transmission over HTTP.",
                    evidence=raw,
                )
            )

        if "httponly" not in flags:
            findings.append(
                Finding(
                    name="Cookie Missing HttpOnly Flag",
                    severity="medium",
                    description=f"Cookie '{name}' is missing the HttpOnly flag.",
                    recommendation="Add the HttpOnly flag to prevent JavaScript access.",
                    evidence=raw,
                )
            )

        if "samesite" not in flags:
            findings.append(
                Finding(
                    name="Cookie Missing SameSite Attribute",
                    severity="low",
                    description=f"Cookie '{name}' is missing the SameSite attribute.",
                    recommendation="Set SameSite=Strict or SameSite=Lax to prevent CSRF.",
                    evidence=raw,
                )
            )
        elif samesite_val == "none" and "secure" not in flags:
            findings.append(
                Finding(
                    name="Cookie SameSite=None Without Secure",
                    severity="medium",
                    description=(
                        f"Cookie '{name}' sets SameSite=None but lacks the Secure flag."
                    ),
                    recommendation="Add the Secure flag when using SameSite=None.",
                    evidence=raw,
                )
            )

        return findings
