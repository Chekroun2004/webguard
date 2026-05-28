"""
Domain ownership API routes.

POST   /domains              → initiate verification (201)
GET    /domains              → list user's domains
GET    /domains/{id}         → domain detail
POST   /domains/{id}/verify  → trigger file or DNS check
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.domain import DomainCreate, DomainOut
from app.services.audit import AuditService
from app.services.domain import (
    DomainAlreadyExistsError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainService,
    DomainVerificationError,
)

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DomainOut)
async def register_domain(
    request: Request,
    body: DomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DomainOut:
    audit = AuditService(db)
    service = DomainService(db)
    try:
        record = await service.register(
            user_id=current_user.id, domain=body.domain, method=body.method
        )
    except DomainAlreadyExistsError as exc:
        await audit.log(
            current_user.id,
            "domain.create",
            target_type="domain",
            status="failure",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Domain already registered"
        ) from exc
    await audit.log(
        current_user.id,
        "domain.create",
        target_type="domain",
        target_id=record.id,
        status="success",
        request=request,
    )
    return DomainOut.model_validate(record)


@router.get("", response_model=list[DomainOut])
async def list_domains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DomainOut]:
    service = DomainService(db)
    records = await service.list_domains(user_id=current_user.id)
    return [DomainOut.model_validate(r) for r in records]


@router.get("/{domain_id}", response_model=DomainOut)
async def get_domain(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DomainOut:
    service = DomainService(db)
    try:
        record = await service.get_domain(domain_id=domain_id, user_id=current_user.id)
    except DomainNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        ) from exc
    except DomainForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    return DomainOut.model_validate(record)


@router.post("/{domain_id}/verify", response_model=DomainOut)
async def verify_domain(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DomainOut:
    service = DomainService(db)
    try:
        record = await service.verify(domain_id=domain_id, user_id=current_user.id)
    except DomainNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        ) from exc
    except DomainForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    except DomainVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DomainOut.model_validate(record)
