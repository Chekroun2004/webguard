from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan
from app.workers.celery_app import celery_app
from app.workers.tasks.scan import run_scan_task

STUCK_THRESHOLD_MINUTES = 10


async def _watchdog_async(session: AsyncSession) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    # TODO: use a started_at column once it exists; created_at is the best proxy for now
    result = await session.execute(
        select(Scan).where(
            Scan.status.in_(["pending", "running"]),
            Scan.created_at < cutoff,
        )
    )
    stuck = result.scalars().all()
    for scan in stuck:
        scan.status = "pending"
    await session.commit()

    for scan in stuck:
        run_scan_task.delay(scan.id)


@celery_app.task(name="watchdog_stuck_scans")
def watchdog_stuck_scans() -> None:
    from app.db.session import task_session

    async def _run() -> None:
        async with task_session() as session:
            await _watchdog_async(session)

    asyncio.run(_run())
