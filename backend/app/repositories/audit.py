"""AuditEvent repository — async DB access only, no business logic."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent


async def create_audit_event(
    db: AsyncSession,
    *,
    user_id: int,
    action: str,
    target_type: str | None,
    target_id: int | None,
    status: str,
    ip: str | None,
    user_agent: str | None,
) -> AuditEvent:
    record = AuditEvent(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        status=status,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(record)
    return record


async def list_audit_events(
    db: AsyncSession,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[AuditEvent], int]:
    """Return (items, total) for a paginated, filtered list scoped to user_id."""
    base = select(AuditEvent).where(AuditEvent.user_id == user_id)
    if action is not None:
        base = base.where(AuditEvent.action == action)
    if status is not None:
        base = base.where(AuditEvent.status == status)
    if date_from is not None:
        base = base.where(AuditEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        base = base.where(AuditEvent.created_at <= datetime.combine(date_to, time.max))

    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar_one()

    paged = (
        base.order_by(AuditEvent.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    items = list((await db.execute(paged)).scalars().all())
    return items, total
