"""Webhooks API routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.webhook import WebhookCreate, WebhookOut, WebhookUpdate
from app.services.webhook import (
    WebhookForbiddenError,
    WebhookNotFoundError,
    WebhookService,
)
from app.services.webhook_sender import build_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WebhookOut)
async def create_webhook_route(
    body: WebhookCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookOut:
    service = WebhookService(db)
    record = await service.create(
        user_id=current_user.id,
        url=str(body.url),
        provider=body.provider,
        is_active=body.is_active,
    )
    return WebhookOut.model_validate(record)


@router.get("", response_model=list[WebhookOut])
async def list_webhooks_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WebhookOut]:
    service = WebhookService(db)
    records = await service.list_for_user(current_user.id)
    return [WebhookOut.model_validate(r) for r in records]


@router.patch("/{webhook_id}", response_model=WebhookOut)
async def update_webhook_route(
    webhook_id: int,
    body: WebhookUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookOut:
    service = WebhookService(db)
    try:
        record = await service.update(
            webhook_id=webhook_id,
            user_id=current_user.id,
            url=str(body.url) if body.url is not None else None,
            provider=body.provider,
            is_active=body.is_active,
        )
    except WebhookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        ) from exc
    except WebhookForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    return WebhookOut.model_validate(record)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_webhook_route(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = WebhookService(db)
    try:
        await service.delete(webhook_id, current_user.id)
    except WebhookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        ) from exc
    except WebhookForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc


@router.post("/{webhook_id}/test", status_code=status.HTTP_200_OK)
async def test_webhook_route(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    """Send a sample payload to the webhook to verify it works."""
    service = WebhookService(db)
    try:
        webhook = await service.get_by_id(webhook_id, current_user.id)
    except WebhookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        ) from exc
    except WebhookForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc

    sample_scan = _SampleScan()
    payload = build_payload(webhook.provider, sample_scan, [])

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook.url, json=payload)
            response.raise_for_status()
        return {"delivered": True}
    except Exception:
        return {"delivered": False}


class _SampleScan:
    """Lightweight stand-in for Scan used by the /test endpoint."""

    id = 0
    url = "https://example.com"
