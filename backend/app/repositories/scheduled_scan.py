"""ScheduledScan repository — async DB access only, no business logic."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scheduled_scan import ScheduledScan


async def create_scheduled_scan(
    db: AsyncSession,
    user_id: int,
    url: str,
    cron_expression: str,
    next_run_at: datetime,
    is_active: bool = True,
) -> ScheduledScan:
    record = ScheduledScan(
        user_id=user_id,
        url=url,
        cron_expression=cron_expression,
        is_active=is_active,
        next_run_at=next_run_at,
    )
    db.add(record)
    await db.flush()
    return record


async def get_scheduled_scan_by_id(db: AsyncSession, scheduled_id: int) -> ScheduledScan | None:
    result = await db.execute(select(ScheduledScan).where(ScheduledScan.id == scheduled_id))
    return result.scalar_one_or_none()


async def list_scheduled_scans_for_user(db: AsyncSession, user_id: int) -> list[ScheduledScan]:
    result = await db.execute(
        select(ScheduledScan)
        .where(ScheduledScan.user_id == user_id)
        .order_by(ScheduledScan.created_at.desc())
    )
    return list(result.scalars().all())


async def list_due_scheduled_scans(db: AsyncSession, now: datetime) -> list[ScheduledScan]:
    result = await db.execute(
        select(ScheduledScan).where(
            ScheduledScan.is_active.is_(True),
            ScheduledScan.next_run_at <= now,
        )
    )
    return list(result.scalars().all())


async def delete_scheduled_scan(db: AsyncSession, record: ScheduledScan) -> None:
    await db.delete(record)
    await db.flush()
