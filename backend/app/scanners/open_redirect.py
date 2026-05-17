"""
OpenRedirectScanner — detects open redirect vulnerabilities.

Looks for redirect-like query parameters in discovered links and tests
whether the application follows an external URL passed in those params.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from app.scanners.base import BaseScanner, Finding
from app.scanners.crawler import CrawledPage, Crawler

REDIRECT_PARAMS = {
    "url",
    "redirect",
    "redirect_url",
    "redirect_uri",
    "next",
    "return",
    "return_url",
    "returnurl",
    "goto",
    "go",
    "dest",
    "destination",
    "target",
    "rurl",
    "redir",
    "location",
}

PROBE_URL = "https://example-evil-redirect.com/"


class OpenRedirectScanner(BaseScanner):
    async def _fetch(self, url: str) -> dict:  # type: ignore[override]
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
            try:
                resp = await client.get(url)
                return {
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text,
                    "final_url": str(resp.url),
                }
            except OSError:
                return {"status": 0, "headers": {}, "body": "", "final_url": url}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        pages: list[CrawledPage] = config.get("pages", [])
        if not pages:
            crawler = Crawler()
            pages = await crawler.crawl(url, config)

        findings: list[Finding] = []
        seen: set[str] = set()
        base_host = urlparse(url).netloc

        for page in pages:
            for link in page.links:
                parsed = urlparse(link)
                params = parse_qs(parsed.query, keep_blank_values=True)
                redirect_keys = [k for k in params if k.lower() in REDIRECT_PARAMS]

                for key in redirect_keys:
                    new_params = {k: v[0] for k, v in params.items()}
                    new_params[key] = PROBE_URL
                    probe_query = urlencode(new_params)
                    probe_url = urlunparse(
                        (
                            parsed.scheme,
                            parsed.netloc,
                            parsed.path,
                            parsed.params,
                            probe_query,
                            "",
                        )
                    )
                    result = await self._fetch(probe_url)
                    location = result["headers"].get("location", "")
                    final = result.get("final_url", "")

                    redirected_out = PROBE_URL in location or (
                        final and urlparse(final).netloc != base_host and final != probe_url
                    )
                    if redirected_out:
                        key_id = f"{parsed.scheme}://{parsed.netloc}{parsed.path}:{key}"
                        if key_id not in seen:
                            seen.add(key_id)
                            findings.append(
                                Finding(
                                    name="Open Redirect",
                                    severity="medium",
                                    description=(
                                        f"The parameter '{key}' on {parsed.path} "
                                        f"allows redirection to external URLs."
                                    ),
                                    recommendation=(
                                        "Validate and whitelist redirect destinations. "
                                        "Never redirect to user-supplied URLs directly."
                                    ),
                                    evidence=(
                                        f"Probed {probe_url} "
                                        f"→ redirected to {location or final}"
                                    ),
                                )
                            )

        return findings
