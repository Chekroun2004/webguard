"""API keys management routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services.api_key import (
    ApiKeyForbiddenError,
    ApiKeyNotFoundError,
    ApiKeyService,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreated)
async def create_key(
    body: ApiKeyCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreated:
    record, plaintext = await ApiKeyService(db).create(user_id=current_user.id, name=body.name)
    base = ApiKeyOut.model_validate(record)
    return ApiKeyCreated(**base.model_dump(), key=plaintext)


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApiKeyOut]:
    records = await ApiKeyService(db).list_for_user(current_user.id)
    return [ApiKeyOut.model_validate(r) for r in records]


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def revoke_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await ApiKeyService(db).revoke(key_id, current_user.id)
    except ApiKeyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        ) from exc
    except ApiKeyForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
