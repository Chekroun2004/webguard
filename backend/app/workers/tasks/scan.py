"""
Celery task for running a scan asynchronously.

Architecture:
  run_scan_task(scan_id)  — sync Celery entry point, calls asyncio.run()
  execute_scan(scan_id, session)  — async business logic, testable directly
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan, Vulnerability
from app.repositories.scan import get_scan_by_id
from app.scanners.headers import HeadersScanner


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

    # 2. Run scanners
    try:
        scanner = HeadersScanner()
        findings = await scanner.scan(str(scan.url), config={})

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
        scan.finished_at = datetime.now(timezone.utc)

    except Exception:
        scan.status = "failed"
        scan.finished_at = datetime.now(timezone.utc)


@shared_task(name="run_scan_task", bind=True, max_retries=0)
def run_scan_task(self, scan_id: int) -> None:
    """Celery entry point — creates a fresh DB session and delegates to execute_scan."""
    from app.db.session import sync_session_factory

    async def _run() -> None:
        async with sync_session_factory() as session:
            await execute_scan(scan_id, session)
            await session.commit()

    asyncio.run(_run())
