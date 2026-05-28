"""Scheduled scans API routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.scheduled_scan import (
    ScheduledScanCreate,
    ScheduledScanOut,
    ScheduledScanUpdate,
)
from app.services.audit import AuditService
from app.services.scheduled_scan import (
    DomainNotVerifiedError,
    InvalidCronError,
    ScheduledScanForbiddenError,
    ScheduledScanNotFoundError,
    ScheduledScanService,
)

router = APIRouter(prefix="/scheduled", tags=["scheduled"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ScheduledScanOut)
async def create_scheduled(
    request: Request,
    body: ScheduledScanCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScheduledScanOut:
    audit = AuditService(db)
    service = ScheduledScanService(db)
    try:
        record = await service.create(
            user_id=current_user.id,
            url=str(body.url),
            cron_expression=body.cron_expression,
            is_active=body.is_active,
        )
    except InvalidCronError as exc:
        await audit.log(
            current_user.id,
            "scheduled.create",
            target_type="scheduled",
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid cron expression",
        ) from exc
    except DomainNotVerifiedError as exc:
        await audit.log(
            current_user.id,
            "scheduled.create",
            target_type="scheduled",
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Domain is not verified",
        ) from exc
    await audit.log(
        current_user.id,
        "scheduled.create",
        target_type="scheduled",
        target_id=record.id,
        status="success",
        request=request,
    )
    return ScheduledScanOut.model_validate(record)


@router.get("", response_model=list[ScheduledScanOut])
async def list_scheduled(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScheduledScanOut]:
    service = ScheduledScanService(db)
    records = await service.list_for_user(current_user.id)
    return [ScheduledScanOut.model_validate(r) for r in records]


@router.get("/{scheduled_id}", response_model=ScheduledScanOut)
async def get_scheduled(
    scheduled_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScheduledScanOut:
    service = ScheduledScanService(db)
    try:
        record = await service.get_by_id(scheduled_id, current_user.id)
    except ScheduledScanNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled scan not found"
        ) from exc
    except ScheduledScanForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    return ScheduledScanOut.model_validate(record)


@router.patch("/{scheduled_id}", response_model=ScheduledScanOut)
async def update_scheduled(
    scheduled_id: int,
    request: Request,
    body: ScheduledScanUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScheduledScanOut:
    audit = AuditService(db)
    service = ScheduledScanService(db)
    try:
        record = await service.update(
            scheduled_id=scheduled_id,
            user_id=current_user.id,
            cron_expression=body.cron_expression,
            is_active=body.is_active,
        )
    except ScheduledScanNotFoundError as exc:
        await audit.log(
            current_user.id,
            "scheduled.update",
            target_type="scheduled",
            target_id=scheduled_id,
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled scan not found"
        ) from exc
    except ScheduledScanForbiddenError as exc:
        await audit.log(
            current_user.id,
            "scheduled.update",
            target_type="scheduled",
            target_id=scheduled_id,
            status="failure",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    except InvalidCronError as exc:
        await audit.log(
            current_user.id,
            "scheduled.update",
            target_type="scheduled",
            target_id=scheduled_id,
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid cron expression",
        ) from exc
    await audit.log(
        current_user.id,
        "scheduled.update",
        target_type="scheduled",
        target_id=record.id,
        status="success",
        request=request,
    )
    return ScheduledScanOut.model_validate(record)


@router.delete(
    "/{scheduled_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_scheduled(
    scheduled_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    audit = AuditService(db)
    service = ScheduledScanService(db)
    try:
        await service.delete(scheduled_id, current_user.id)
    except ScheduledScanNotFoundError as exc:
        await audit.log(
            current_user.id,
            "scheduled.delete",
            target_type="scheduled",
            target_id=scheduled_id,
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled scan not found"
        ) from exc
    except ScheduledScanForbiddenError as exc:
        await audit.log(
            current_user.id,
            "scheduled.delete",
            target_type="scheduled",
            target_id=scheduled_id,
            status="failure",
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    await audit.log(
        current_user.id,
        "scheduled.delete",
        target_type="scheduled",
        target_id=scheduled_id,
        status="success",
        request=request,
    )
