"""
CsrfScanner — detects POST forms that lack CSRF token fields.

Checks each discovered POST form for the presence of common CSRF token
input names. GET forms are not flagged (they don't require CSRF protection).
"""

from __future__ import annotations

from app.scanners.base import BaseScanner, Finding
from app.scanners.crawler import CrawledPage, Crawler

CSRF_TOKEN_NAMES = {
    "_token",
    "csrf",
    "csrf_token",
    "csrftoken",
    "csrfmiddlewaretoken",
    "_csrf",
    "_csrf_token",
    "xsrf_token",
    "xsrftoken",
    "authenticity_token",
    "verify_token",
    "request_token",
}


class CsrfScanner(BaseScanner):
    async def scan(self, url: str, config: dict) -> list[Finding]:
        pages: list[CrawledPage] = config.get("pages", [])
        if not pages:
            crawler = Crawler()
            pages = await crawler.crawl(url, config)

        findings: list[Finding] = []

        for page in pages:
            for form in page.forms:
                if form.method.lower() != "post":
                    continue
                input_names = {i["name"].lower() for i in form.inputs}
                has_token = bool(input_names & CSRF_TOKEN_NAMES)
                if not has_token:
                    findings.append(
                        Finding(
                            name="Missing CSRF Protection",
                            severity="high",
                            description=(
                                f"The POST form at '{form.action}' does not contain "
                                f"a CSRF token field."
                            ),
                            recommendation=(
                                "Add a CSRF token to all state-changing forms and "
                                "validate it server-side on every request."
                            ),
                            evidence=f"Form action: {form.action} — no CSRF token input found.",
                        )
                    )

        return findings
