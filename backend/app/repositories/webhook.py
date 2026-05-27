"""Webhook repository — async DB access only, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.webhook import Webhook


async def create_webhook(
    db: AsyncSession,
    user_id: int,
    url: str,
    provider: str,
    is_active: bool = True,
) -> Webhook:
    record = Webhook(user_id=user_id, url=url, provider=provider, is_active=is_active)
    db.add(record)
    await db.flush()
    return record


async def get_webhook_by_id(db: AsyncSession, webhook_id: int) -> Webhook | None:
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    return result.scalar_one_or_none()


async def list_webhooks_for_user(db: AsyncSession, user_id: int) -> list[Webhook]:
    result = await db.execute(
        select(Webhook).where(Webhook.user_id == user_id).order_by(Webhook.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_webhooks_for_user(db: AsyncSession, user_id: int) -> list[Webhook]:
    result = await db.execute(
        select(Webhook).where(Webhook.user_id == user_id, Webhook.is_active.is_(True))
    )
    return list(result.scalars().all())


async def delete_webhook(db: AsyncSession, record: Webhook) -> None:
    await db.delete(record)
    await db.flush()
