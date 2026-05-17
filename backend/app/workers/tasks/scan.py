"""
Celery task for running a scan asynchronously.

Architecture:
  run_scan_task(scan_id)  — sync Celery entry point, calls asyncio.run()
  execute_scan(scan_id, session)  — async business logic, testable directly
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Vulnerability
from app.repositories.scan import get_scan_by_id
from app.scanners.cookies import CookiesScanner
from app.scanners.headers import HeadersScanner
from app.scanners.http_methods import HttpMethodsScanner
from app.scanners.sensitive_files import SensitiveFilesScanner
from app.scanners.ssl_tls import SslTlsScanner
from app.scanners.technologies import TechnologiesScanner
from app.workers.celery_app import celery_app

SCANNERS = [
    HeadersScanner,
    CookiesScanner,
    SslTlsScanner,
    SensitiveFilesScanner,
    TechnologiesScanner,
    HttpMethodsScanner,
]


async def execute_scan(scan_id: int, session: AsyncSession) -> None:
    """
    Core async logic: run all scanners for the given scan and persist findings.

    Accepts an explicit session so tests can inject the in-memory SQLite session.
    The Celery task creates its own session from the production factory.
    """
    # 1. Mark as running
    scan = await get_scan_by_id(session, scan_id)
    if scan is None:
        return  # scan deleted before task ran — nothing to do

    scan.status = "running"
    await session.flush()

    # 2. Run all scanners concurrently
    try:
        url = str(scan.url)
        results = await asyncio.gather(
            *[cls().scan(url, config={}) for cls in SCANNERS],
            return_exceptions=True,
        )

        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            raise errors[0]

        findings = [f for batch in results if isinstance(batch, list) for f in batch]

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
