"""
Celery task for running a scan asynchronously.

Architecture:
  run_scan_task(scan_id)  — sync Celery entry point, calls asyncio.run()
  execute_scan(scan_id, session)  — async business logic, testable directly

Scan flow:
  1. Passive scanners (Phase 1) run concurrently on the base URL.
  2. Crawler discovers pages and forms on the target site.
  3. Active scanners (Phase 2) run concurrently using crawled pages.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Vulnerability
from app.repositories.scan import get_scan_by_id
from app.scanners.cookies import CookiesScanner
from app.scanners.crawler import Crawler
from app.scanners.csrf import CsrfScanner
from app.scanners.directory_listing import DirectoryListingScanner
from app.scanners.headers import HeadersScanner
from app.scanners.http_methods import HttpMethodsScanner
from app.scanners.open_redirect import OpenRedirectScanner
from app.scanners.sensitive_files import SensitiveFilesScanner
from app.scanners.sqli import SqliScanner
from app.scanners.ssl_tls import SslTlsScanner
from app.scanners.technologies import TechnologiesScanner
from app.scanners.xss import XssScanner
from app.workers.celery_app import celery_app

PASSIVE_SCANNERS = [
    HeadersScanner,
    CookiesScanner,
    SslTlsScanner,
    SensitiveFilesScanner,
    TechnologiesScanner,
    HttpMethodsScanner,
]

ACTIVE_SCANNERS = [
    XssScanner,
    SqliScanner,
    OpenRedirectScanner,
    CsrfScanner,
    DirectoryListingScanner,
]

# Backward-compat alias used by tests that mock SCANNERS directly.
SCANNERS = PASSIVE_SCANNERS


async def execute_scan(scan_id: int, session: AsyncSession) -> None:
    """
    Core async logic: run all scanners for the given scan and persist findings.

    Accepts an explicit session so tests can inject the in-memory SQLite session.
    The Celery task creates its own session from the production factory.
    """
    scan = await get_scan_by_id(session, scan_id)
    if scan is None:
        return

    scan.status = "running"
    await session.flush()

    try:
        url = str(scan.url)

        # Phase 1 — passive scanners (no crawl needed)
        passive_results = await asyncio.gather(
            *[cls().scan(url, {}) for cls in SCANNERS],
            return_exceptions=True,
        )

        passive_errors = [r for r in passive_results if isinstance(r, BaseException)]
        if passive_errors:
            raise passive_errors[0]

        # Phase 2 — crawl then run active scanners
        crawler = Crawler()
        try:
            pages = await crawler.crawl(url, {})
        except Exception:
            pages = []

        active_config = {"pages": pages}
        active_results = await asyncio.gather(
            *[cls().scan(url, active_config) for cls in ACTIVE_SCANNERS],
            return_exceptions=True,
        )

        all_results = list(passive_results) + list(active_results)
        findings = [f for batch in all_results if isinstance(batch, list) for f in batch]

        for f in findings:
            session.add(
                Vulnerability(
                    scan_id=scan.id,
                    name=f.name,
                    severity=f.severity,
                    description=f.description,
                    recommendation=f.recommendation,
                    evidence=f.evidence,
                )
            )

        scan.status = "completed"
        scan.finished_at = datetime.now(UTC)

    except Exception:
        scan.status = "failed"
        scan.finished_at = datetime.now(UTC)


@celery_app.task(name="run_scan_task")
def run_scan_task(scan_id: int) -> None:
    """Celery entry point — creates a fresh DB session and delegates to execute_scan."""
    from app.db.session import sync_session_factory

    async def _run() -> None:
        async with sync_session_factory() as session:
            await execute_scan(scan_id, session)
            await session.commit()

    asyncio.run(_run())
