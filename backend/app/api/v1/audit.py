"""Audit log API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.repositories.audit import list_audit_events
from app.schemas.audit import AuditAction, AuditEventList, AuditEventOut, AuditStatus

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditEventList)
async def list_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: AuditAction | None = Query(default=None),
    status: AuditStatus | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditEventList:
    items, total = await list_audit_events(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        action=action,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditEventList(
        items=[AuditEventOut.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )
