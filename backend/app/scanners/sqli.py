"""
SqliScanner — detects error-based SQL injection vulnerabilities.

Injects SQL payloads into form inputs and checks for database error strings
in the response body.
"""

from __future__ import annotations

import re

import httpx

from app.scanners.base import BaseScanner, Finding
from app.scanners.crawler import CrawledPage, Crawler

SQLI_PAYLOADS = [
    "'",
    "' OR '1'='1",
    '" OR "1"="1',
    "1; DROP TABLE users--",
]

SQL_ERROR_PATTERNS = re.compile(
    r"(SQL syntax|mysql_fetch|mysql_num_rows|mysqli_|pg_query|"
    r"ORA-\d{4,5}|SQLSTATE\[\d{5}\]|sqlite3\.OperationalError|"
    r"Unclosed quotation mark|Microsoft OLE DB Provider for SQL)",
    re.IGNORECASE,
)

SAFE_INPUT_TYPES = {"hidden", "password", "file", "checkbox", "radio", "submit"}


class SqliScanner(BaseScanner):
    async def _submit_form(
        self,
        action: str,
        method: str,
        data: dict,
        cookies: dict[str, str] | None = None,
    ) -> dict:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15, cookies=cookies or {}
        ) as client:
            try:
                if method == "post":
                    resp = await client.post(action, data=data)
                else:
                    resp = await client.get(action, params=data)
                return {"status": resp.status_code, "body": resp.text}
            except OSError:
                return {"status": 0, "body": ""}

    async def scan(self, url: str, config: dict) -> list[Finding]:
        cookies = config.get("cookies")
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
                    for payload in SQLI_PAYLOADS:
                        data = {i["name"]: i["value"] for i in form.inputs}
                        data[inp["name"]] = payload
                        result = await self._submit_form(
                            form.action, form.method, data, cookies=cookies
                        )
                        if SQL_ERROR_PATTERNS.search(result.get("body", "")):
                            key = f"{form.action}:{inp['name']}"
                            if key not in seen:
                                seen.add(key)
                                findings.append(
                                    Finding(
                                        name="SQL Injection",
                                        severity="critical",
                                        description=(
                                            f"SQL error triggered in parameter "
                                            f"'{inp['name']}' on {form.action}."
                                        ),
                                        recommendation=(
                                            "Use parameterised queries or prepared statements. "
                                            "Never concatenate user input into SQL strings."
                                        ),
                                        evidence=(
                                            f"Payload '{payload}' triggered a database error."
                                        ),
                                    )
                                )
                            break

        return findings
