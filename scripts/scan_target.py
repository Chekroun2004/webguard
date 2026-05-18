#!/usr/bin/env python3
"""
scan_target.py — runs WebGuard's passive scanners against a target URL.

Usage:
    python scripts/scan_target.py http://localhost:3000

This helper is designed for CI smoke-testing the scanner pack against a known
vulnerable target (e.g. OWASP Juice Shop). Only the fast, passive scanners are
invoked — active scanners (XSS, SQLi, CSRF, open redirect, directory listing)
rely on the crawler and are too slow / flaky for a CI assertion job.

Exit codes:
    0 — at least 3 findings of severity in {"high", "medium"} were produced
    1 — fewer than 3 high/medium findings (scanner effectiveness regression)
    2 — usage error
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
from pathlib import Path

# Make `backend/` importable when this script is run from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scanners.base import BaseScanner, Finding  # noqa: E402
from app.scanners.cookies import CookiesScanner  # noqa: E402
from app.scanners.headers import HeadersScanner  # noqa: E402
from app.scanners.http_methods import HttpMethodsScanner  # noqa: E402
from app.scanners.sensitive_files import SensitiveFilesScanner  # noqa: E402
from app.scanners.technologies import TechnologiesScanner  # noqa: E402

# Passive scanners only — fast, deterministic, no crawler required.
PASSIVE_SCANNERS: list[type[BaseScanner]] = [
    HeadersScanner,
    CookiesScanner,
    TechnologiesScanner,
    HttpMethodsScanner,
    SensitiveFilesScanner,
]

ASSERT_SEVERITIES = {"high", "medium"}
ASSERT_MIN_FINDINGS = 3


async def run_all(url: str) -> list[Finding]:
    scanners = [cls() for cls in PASSIVE_SCANNERS]
    results = await asyncio.gather(
        *(s.scan(url, {}) for s in scanners),
        return_exceptions=True,
    )
    findings: list[Finding] = []
    for scanner, result in zip(scanners, results):
        if isinstance(result, Exception):
            print(
                f"warning: {scanner.__class__.__name__} raised {type(result).__name__}: {result}",
                file=sys.stderr,
            )
            continue
        findings.extend(result)
    return findings


def serialize(findings: list[Finding]) -> list[dict]:
    return [dataclasses.asdict(f) for f in findings]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scan_target.py <url>", file=sys.stderr)
        return 2
    url = sys.argv[1]

    findings = asyncio.run(run_all(url))
    payload = {
        "target": url,
        "total": len(findings),
        "findings": serialize(findings),
    }
    print(json.dumps(payload, indent=2, default=str))

    qualifying = [f for f in findings if f.severity in ASSERT_SEVERITIES]
    print(
        f"\nAssertion: {len(qualifying)} findings with severity in {sorted(ASSERT_SEVERITIES)} "
        f"(need >= {ASSERT_MIN_FINDINGS})",
        file=sys.stderr,
    )

    if len(qualifying) >= ASSERT_MIN_FINDINGS:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
