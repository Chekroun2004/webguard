"""Webhook service — CRUD business rules + custom exceptions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.webhook import Webhook
from app.repositories.webhook import (
    create_webhook,
    delete_webhook,
    get_webhook_by_id,
    list_webhooks_for_user,
)


class WebhookNotFoundError(Exception):
    pass


class WebhookForbiddenError(Exception):
    pass


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: int,
        url: str,
        provider: str,
        is_active: bool = True,
    ) -> Webhook:
        return await create_webhook(
            self._db,
            user_id=user_id,
            url=url,
            provider=provider,
            is_active=is_active,
        )

    async def list_for_user(self, user_id: int) -> list[Webhook]:
        return await list_webhooks_for_user(self._db, user_id)

    async def get_by_id(self, webhook_id: int, user_id: int) -> Webhook:
        record = await get_webhook_by_id(self._db, webhook_id)
        if record is None:
            raise WebhookNotFoundError
        if record.user_id != user_id:
            raise WebhookForbiddenError
        return record

    async def update(
        self,
        *,
        webhook_id: int,
        user_id: int,
        url: str | None,
        provider: str | None,
        is_active: bool | None,
    ) -> Webhook:
        record = await self.get_by_id(webhook_id, user_id)
        if url is not None:
            record.url = url
        if provider is not None:
            record.provider = provider
        if is_active is not None:
            record.is_active = is_active
        await self._db.flush()
        return record

    async def delete(self, webhook_id: int, user_id: int) -> None:
        record = await self.get_by_id(webhook_id, user_id)
        await delete_webhook(self._db, record)
