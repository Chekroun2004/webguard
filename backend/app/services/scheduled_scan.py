"""ScheduledScan service — business rules + custom exceptions."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.domain import DomainOwnership
from app.db.models.scheduled_scan import ScheduledScan
from app.repositories.scheduled_scan import (
    create_scheduled_scan,
    delete_scheduled_scan,
    get_scheduled_scan_by_id,
    list_scheduled_scans_for_user,
)


class ScheduledScanNotFoundError(Exception):
    pass


class ScheduledScanForbiddenError(Exception):
    pass


class InvalidCronError(Exception):
    pass


class DomainNotVerifiedError(Exception):
    pass


def _normalize_url(raw: str) -> str:
    """Strip trailing slash and lowercase scheme/host."""
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    netloc = host + (f":{parsed.port}" if parsed.port else "")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{netloc}{path}"


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


class ScheduledScanService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: int,
        url: str,
        cron_expression: str,
        is_active: bool = True,
    ) -> ScheduledScan:
        if not croniter.is_valid(cron_expression):
            raise InvalidCronError(cron_expression)

        normalized = _normalize_url(url)

        if not await _is_domain_verified(self._db, user_id, normalized):
            raise DomainNotVerifiedError(normalized)

        now = datetime.now(UTC)
        next_run_at = croniter(cron_expression, now).get_next(datetime)
        return await create_scheduled_scan(
            self._db,
            user_id=user_id,
            url=normalized,
            cron_expression=cron_expression,
            next_run_at=next_run_at,
            is_active=is_active,
        )

    async def list_for_user(self, user_id: int) -> list[ScheduledScan]:
        return await list_scheduled_scans_for_user(self._db, user_id)

    async def get_by_id(self, scheduled_id: int, user_id: int) -> ScheduledScan:
        record = await get_scheduled_scan_by_id(self._db, scheduled_id)
        if record is None:
            raise ScheduledScanNotFoundError
        if record.user_id != user_id:
            raise ScheduledScanForbiddenError
        return record

    async def update(
        self,
        *,
        scheduled_id: int,
        user_id: int,
        cron_expression: str | None,
        is_active: bool | None,
    ) -> ScheduledScan:
        record = await self.get_by_id(scheduled_id, user_id)
        if cron_expression is not None:
            if not croniter.is_valid(cron_expression):
                raise InvalidCronError(cron_expression)
            record.cron_expression = cron_expression
            record.next_run_at = croniter(cron_expression, datetime.now(UTC)).get_next(datetime)
        if is_active is not None:
            record.is_active = is_active
        await self._db.flush()
        return record

    async def delete(self, scheduled_id: int, user_id: int) -> None:
        record = await self.get_by_id(scheduled_id, user_id)
        await delete_scheduled_scan(self._db, record)
