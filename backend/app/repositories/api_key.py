"""ApiKey repository — async DB access only, no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import ApiKey


async def create_api_key(
    db: AsyncSession,
    user_id: int,
    name: str,
    prefix: str,
    hashed_key: str,
) -> ApiKey:
    record = ApiKey(
        user_id=user_id,
        name=name,
        prefix=prefix,
        hashed_key=hashed_key,
    )
    db.add(record)
    await db.flush()
    return record


async def get_api_key_by_id(db: AsyncSession, key_id: int) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    return result.scalar_one_or_none()


async def get_api_key_by_hash(db: AsyncSession, hashed_key: str) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.hashed_key == hashed_key))
    return result.scalar_one_or_none()


async def list_api_keys_for_user(db: AsyncSession, user_id: int) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())
