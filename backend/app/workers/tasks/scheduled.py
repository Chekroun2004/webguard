"""Celery Beat task: trigger due ScheduledScan rows."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.domain import DomainOwnership
from app.db.models.scan import Scan
from app.db.models.scheduled_scan import ScheduledScan
from app.repositories.scheduled_scan import list_due_scheduled_scans
from app.workers.celery_app import celery_app
from app.workers.tasks.scan import run_scan_task

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


async def _is_domain_verified(db: AsyncSession, user_id: int, url: str) -> bool:
    domain = _extract_domain(url)
    if not domain:
        return False
    result = await db.execute(
        select(DomainOwnership).where(
            DomainOwnership.user_id == user_id,
            DomainOwnership.domain == domain,
            DomainOwnership.is_verified.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def _previous_still_running(db: AsyncSession, sched: ScheduledScan) -> bool:
    if sched.last_run_at is None:
        return False
    result = await db.execute(
        select(Scan.id)
        .where(
            Scan.user_id == sched.user_id,
            Scan.url == sched.url,
            Scan.status.in_(["pending", "running"]),
            Scan.created_at >= sched.last_run_at,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _run_due_scheduled_scans(db: AsyncSession) -> dict[str, int]:
    """Execute due scheduled scans. Returns counts for observability."""
    triggered = skipped_unverified = skipped_overlap = 0
    now = datetime.now(UTC)
    due = await list_due_scheduled_scans(db, now)

    for sched in due:
        if not await _is_domain_verified(db, sched.user_id, sched.url):
            sched.is_active = False
            logger.warning(
                "scheduled_scan %d disabled: domain unverified for user %d",
                sched.id,
                sched.user_id,
            )
            skipped_unverified += 1
            continue

        if await _previous_still_running(db, sched):
            sched.next_run_at = croniter(sched.cron_expression, now).get_next(datetime)
            logger.warning(
                "scheduled_scan %d skipped: previous scan still running",
                sched.id,
            )
            skipped_overlap += 1
            continue

        scan = Scan(user_id=sched.user_id, url=sched.url, status="pending")
        db.add(scan)
        await db.flush()
        sched.last_run_at = now
        sched.next_run_at = croniter(sched.cron_expression, now).get_next(datetime)
        run_scan_task.delay(scan.id)
        triggered += 1

    await db.commit()
    return {
        "triggered": triggered,
        "skipped_unverified": skipped_unverified,
        "skipped_overlap": skipped_overlap,
    }


@celery_app.task(name="run_due_scheduled_scans")
def run_due_scheduled_scans() -> dict[str, int]:
    """Celery Beat entrypoint — creates a fresh session and delegates."""
    from app.db.session import task_session

    async def _run() -> dict[str, int]:
        async with task_session() as session:
            return await _run_due_scheduled_scans(session)

    return asyncio.run(_run())
