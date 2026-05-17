"""Domain ownership repository — DB access only, no business logic."""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.domain import DomainOwnership


async def create_domain_record(
    db: AsyncSession, user_id: int, domain: str, method: str
) -> DomainOwnership:
    record = DomainOwnership(
        user_id=user_id,
        domain=domain,
        verification_method=method,
        verification_token=secrets.token_hex(32),
    )
    db.add(record)
    await db.flush()
    return record


async def get_domain_by_id(db: AsyncSession, domain_id: int) -> DomainOwnership | None:
    result = await db.execute(
        select(DomainOwnership).where(DomainOwnership.id == domain_id)
    )
    return result.scalar_one_or_none()


async def get_domain_by_user_and_name(
    db: AsyncSession, user_id: int, domain: str
) -> DomainOwnership | None:
    result = await db.execute(
        select(DomainOwnership).where(
            DomainOwnership.user_id == user_id,
            DomainOwnership.domain == domain,
        )
    )
    return result.scalar_one_or_none()


async def list_domains_for_user(db: AsyncSession, user_id: int) -> list[DomainOwnership]:
    result = await db.execute(
        select(DomainOwnership)
        .where(DomainOwnership.user_id == user_id)
        .order_by(DomainOwnership.created_at.desc())
    )
    return list(result.scalars().all())
