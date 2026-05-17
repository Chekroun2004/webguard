"""
XssScanner — detects reflected Cross-Site Scripting (XSS) vulnerabilities.

Tests each text/email/search input in discovered forms by injecting payloads
and checking whether the payload appears verbatim in the response body.
"""

from __future__ import annotations

import httpx

from app.scanners.base import BaseScanner, Finding
from app.scanners.crawler import CrawledPage, Crawler

XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    '"><svg onload=alert(1)>',
]

SAFE_INPUT_TYPES = {"hidden", "password", "file", "checkbox", "radio", "submit"}


class XssScanner(BaseScanner):
    async def _submit_form(self, action: str, method: str, data: dict) -> dict:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            try:
                if method == "post":
                    resp = await client.post(action, data=data)
                else:
                    resp = await client.get(action, params=data)
                return {"status": resp.status_code, "body": resp.text}
            except OSError:
                return {"status": 0, "body": ""}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        pages: list[CrawledPage] = config.get("pages", [])
        if not pages:
            crawler = Crawler()
            pages = await crawler.crawl(url, config)

        findings: list[Finding] = []
        seen: set[str] = set()

        for page in pages:
            for form in page.forms:
                for inp in form.inputs:
                    if inp["type"] in SAFE_INPUT_TYPES:
                        continue
                    for payload in XSS_PAYLOADS:
                        data = {i["name"]: i["value"] for i in form.inputs}
                        data[inp["name"]] = payload
                        result = await self._submit_form(form.action, form.method, data)
                        if payload in result.get("body", ""):
                            key = f"{form.action}:{inp['name']}"
                            if key not in seen:
                                seen.add(key)
                                findings.append(
                                    Finding(
                                        name="Cross-Site Scripting (XSS)",
                                        severity="high",
                                        description=(
                                            f"Reflected XSS found in parameter "
                                            f"'{inp['name']}' on {form.action}."
                                        ),
                                        recommendation=(
                                            "Encode all user input before rendering it "
                                            "in HTML. Implement a strict Content-Security-Policy."
                                        ),
                                        evidence=f"Payload '{payload}' reflected in response.",
                                    )
                                )
                            break

        return findings
