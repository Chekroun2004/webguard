"""
SecurityTxtScanner — checks for /.well-known/security.txt (RFC 9116).

Findings:
  - 404 / not found              → info ("Missing /.well-known/security.txt")
  - 200 but empty / no Contact:  → low  ("Incomplete security.txt")
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

import httpx

from app.scanners.base import BaseScanner, Finding

SECURITY_TXT_PATH = "/.well-known/security.txt"


def _base_url(url: str) -> str:
    """Return scheme://netloc for the given URL (strip path / query / fragment)."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


class SecurityTxtScanner(BaseScanner):
    async def _fetch(self, url: str) -> dict:  # type: ignore[override]
        target = _base_url(url).rstrip("/") + SECURITY_TXT_PATH
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(target)
            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
                "url": target,
            }

    async def scan(self, url: str, config: dict) -> list[Finding]:
        try:
            response = await self._fetch(url)
        except Exception:
            # Network errors are not a security finding per se — stay silent.
            return []

        status = response.get("status", 0)
        body = response.get("body", "") or ""
        target = response.get("url", _base_url(url) + SECURITY_TXT_PATH)

        if status == 200:
            stripped = body.strip()
            has_contact = any(
                line.strip().lower().startswith("contact:")
                for line in stripped.splitlines()
            )
            if not stripped or not has_contact:
                return [
                    Finding(
                        name="Incomplete security.txt",
                        severity="low",
                        description=(
                            "A security.txt file is served but it is empty or "
                            "missing the required Contact: field (RFC 9116)."
                        ),
                        recommendation=(
                            "Provide at least a Contact: field (mailto:, https:// or tel:) "
                            "and ideally Expires:, Encryption:, Policy: per RFC 9116."
                        ),
                        evidence=f"GET {target} → {status}, body length={len(body)}",
                    )
                ]
            return []

        # Anything other than 200 (404, 403, 5xx, ...) → file effectively absent.
        return [
            Finding(
                name="Missing /.well-known/security.txt",
                severity="info",
                description=(
                    "No security.txt file was found at /.well-known/security.txt. "
                    "RFC 9116 recommends publishing one so researchers can report "
                    "vulnerabilities."
                ),
                recommendation=(
                    "Publish a security.txt at /.well-known/security.txt with at "
                    "least a Contact: field. See https://securitytxt.org/."
                ),
                evidence=f"GET {target} → HTTP {status}",
            )
        ]
