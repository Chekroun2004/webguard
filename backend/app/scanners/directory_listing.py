"""
DirectoryListingScanner — checks common directories for enabled directory listing.

Fetches a list of common upload/asset directories and looks for
"Index of" patterns in the response body, which indicate directory browsing is on.
"""

from __future__ import annotations

import re

import httpx

from app.scanners.base import BaseScanner, Finding

COMMON_DIRS = [
    "/uploads/",
    "/files/",
    "/static/",
    "/assets/",
    "/images/",
    "/backup/",
    "/logs/",
    "/temp/",
    "/cache/",
    "/data/",
]

DIR_LISTING_PATTERN = re.compile(
    r"(Index of /|Directory listing for |Parent Directory)", re.IGNORECASE
)


class DirectoryListingScanner(BaseScanner):
    async def _check_dir(self, url: str) -> dict:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            try:
                resp = await client.get(url)
                return {"status": resp.status_code, "body": resp.text}
            except OSError:
                return {"status": 0, "body": ""}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        base = url.rstrip("/")
        findings: list[Finding] = []

        for directory in COMMON_DIRS:
            target = base + directory
            result = await self._check_dir(target)
            if result["status"] == 200 and DIR_LISTING_PATTERN.search(result.get("body", "")):
                findings.append(
                    Finding(
                        name="Directory Listing Enabled",
                        severity="medium",
                        description=(
                            f"Directory listing is enabled at '{directory}', "
                            f"exposing file system contents."
                        ),
                        recommendation=(
                            "Disable directory listing in your web server configuration "
                            "(e.g., Options -Indexes in Apache, autoindex off in Nginx)."
                        ),
                        evidence=target,
                    )
                )

        return findings
