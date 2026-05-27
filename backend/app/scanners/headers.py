"""
HeadersScanner — checks HTTP security headers.

Checks:
  - Presence of: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
  - Quality of: CSP (unsafe-inline / unsafe-eval), HSTS (max-age >= 31536000)
"""

from __future__ import annotations

import re

from app.scanners.base import BaseScanner, Finding

# Minimum HSTS max-age considered secure (1 year in seconds)
MIN_HSTS_MAX_AGE = 31_536_000


class HeadersScanner(BaseScanner):
    REQUIRED_HEADERS = [
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Referrer-Policy",
    ]

    async def scan(self, url: str, config: dict) -> list[Finding]:
        response = await self._fetch(url, cookies=config.get("cookies"))
        # Normalize header keys to title-case for consistent lookup
        headers: dict[str, str] = {k.title(): v for k, v in response["headers"].items()}

        findings: list[Finding] = []

        # --- Presence checks ---
        for header in self.REQUIRED_HEADERS:
            if header not in headers:
                findings.append(
                    Finding(
                        name=f"Missing {header}",
                        severity=self._missing_severity(header),
                        description=f"The HTTP response does not include the '{header}' header.",
                        recommendation=f"Add the '{header}' header to all HTTP responses.",
                    )
                )

        # --- Quality checks (only when header is present) ---
        if "Content-Security-Policy" in headers:
            findings.extend(self._check_csp(headers["Content-Security-Policy"]))

        if "Strict-Transport-Security" in headers:
            findings.extend(self._check_hsts(headers["Strict-Transport-Security"]))

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _missing_severity(self, header: str) -> str:
        mapping = {
            "Content-Security-Policy": "high",
            "Strict-Transport-Security": "high",
            "X-Frame-Options": "medium",
            "X-Content-Type-Options": "medium",
            "Referrer-Policy": "low",
            "Permissions-Policy": "low",
        }
        return mapping.get(header, "low")

    def _check_csp(self, value: str) -> list[Finding]:
        findings = []
        if "'unsafe-inline'" in value or "'unsafe-eval'" in value:
            findings.append(
                Finding(
                    name="Weak Content-Security-Policy",
                    severity="medium",
                    description=(
                        "The Content-Security-Policy header contains 'unsafe-inline' or "
                        "'unsafe-eval', which weakens XSS protections."
                    ),
                    recommendation="Remove 'unsafe-inline' and 'unsafe-eval' from the CSP.",
                    evidence=value,
                )
            )
        return findings

    def _check_hsts(self, value: str) -> list[Finding]:
        findings = []
        match = re.search(r"max-age=(\d+)", value, re.IGNORECASE)
        if match:
            max_age = int(match.group(1))
            if max_age < MIN_HSTS_MAX_AGE:
                findings.append(
                    Finding(
                        name="Weak Strict-Transport-Security",
                        severity="medium",
                        description=(
                            f"HSTS max-age is {max_age}s, which is below the recommended "
                            f"minimum of {MIN_HSTS_MAX_AGE}s (1 year)."
                        ),
                        recommendation="Set max-age to at least 31536000 (1 year).",
                        evidence=value,
                    )
                )
        return findings
