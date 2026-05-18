"""
CorsScanner — detects CORS misconfigurations.

Strategy:
  Send a GET request with an attacker-controlled Origin header. Inspect
  Access-Control-Allow-Origin / Access-Control-Allow-Credentials in the response.

Findings:
  - ACAO reflects the attacker origin AND ACAC=true   → high
  - ACAO == "*" AND ACAC=true                         → high (browser would
        actually refuse, but the server config is dangerous)
  - ACAO == "*"                                       → medium
  - ACAO reflects the attacker origin (no credentials) → medium
  - No CORS headers at all                            → no finding
"""

from __future__ import annotations

import httpx

from app.scanners.base import BaseScanner, Finding

EVIL_ORIGIN = "https://evil.example.com"


class CorsScanner(BaseScanner):
    async def _fetch(self, url: str) -> dict:  # type: ignore[override]
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(url, headers={"Origin": EVIL_ORIGIN})
            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
            }

    async def scan(self, url: str, config: dict) -> list[Finding]:
        response = await self._fetch(url)
        headers = {k.lower(): v for k, v in response["headers"].items()}

        acao = headers.get("access-control-allow-origin")
        acac = headers.get("access-control-allow-credentials", "").strip().lower() == "true"

        # No CORS headers at all → could be intentional, no finding.
        if acao is None:
            return []

        findings: list[Finding] = []
        evidence = (
            f"Access-Control-Allow-Origin: {acao}; "
            f"Access-Control-Allow-Credentials: {headers.get('access-control-allow-credentials', '')}"
        )

        if acao.strip() == EVIL_ORIGIN and acac:
            findings.append(
                Finding(
                    name="CORS dangerously permissive",
                    severity="high",
                    description=(
                        "The server reflects an arbitrary Origin in "
                        "Access-Control-Allow-Origin and allows credentials. "
                        "This lets any attacker-controlled site read authenticated "
                        "responses from this endpoint."
                    ),
                    recommendation=(
                        "Validate the Origin header against an allow-list. "
                        "Never reflect arbitrary origins when credentials are allowed."
                    ),
                    evidence=evidence,
                )
            )
        elif acao.strip() == "*" and acac:
            findings.append(
                Finding(
                    name="CORS dangerously permissive",
                    severity="high",
                    description=(
                        "Access-Control-Allow-Origin: * combined with "
                        "Access-Control-Allow-Credentials: true is an invalid and "
                        "dangerous configuration."
                    ),
                    recommendation=(
                        "Either restrict the origin to a specific allow-list, or "
                        "remove Access-Control-Allow-Credentials when using '*'."
                    ),
                    evidence=evidence,
                )
            )
        elif acao.strip() == "*":
            findings.append(
                Finding(
                    name="CORS wildcard origin",
                    severity="medium",
                    description=(
                        "The endpoint exposes Access-Control-Allow-Origin: * which "
                        "allows any origin to read non-credentialed responses."
                    ),
                    recommendation=(
                        "Restrict Access-Control-Allow-Origin to specific trusted origins."
                    ),
                    evidence=evidence,
                )
            )
        elif acao.strip() == EVIL_ORIGIN:
            findings.append(
                Finding(
                    name="CORS reflects arbitrary origin",
                    severity="medium",
                    description=(
                        "The server reflects arbitrary Origin values in "
                        "Access-Control-Allow-Origin. Without credentials this is "
                        "less critical but still indicates a permissive policy."
                    ),
                    recommendation=(
                        "Validate the Origin header against an allow-list rather than "
                        "reflecting it."
                    ),
                    evidence=evidence,
                )
            )

        return findings
