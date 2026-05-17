"""
Scan API routes — POST /scans, GET /scans, GET /scans/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.scan import ScanCreate, ScanOut, VulnerabilityOut
from app.services.scan import ScanForbiddenError, ScanNotFoundError, ScanService

router = APIRouter(prefix="/scans", tags=["scans"])


def _scan_to_out(scan) -> ScanOut:
    return ScanOut(
        id=scan.id,
        url=str(scan.url),
        status=scan.status,
        created_at=scan.created_at,
        finished_at=scan.finished_at,
        findings=[
            VulnerabilityOut(
                id=v.id,
                name=v.name,
                severity=v.severity,
                description=v.description,
                recommendation=v.recommendation,
                evidence=v.evidence,
            )
            for v in scan.vulnerabilities
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ScanOut)
async def create_scan(
    body: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanOut:
    service = ScanService(db)
    scan = await service.run_scan(user_id=current_user.id, url=str(body.url))
    return _scan_to_out(scan)


@router.get("", response_model=list[ScanOut])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScanOut]:
    service = ScanService(db)
    scans = await service.list_scans(user_id=current_user.id)
    return [_scan_to_out(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanOut:
    service = ScanService(db)
    try:
        scan = await service.get_scan(scan_id=scan_id, user_id=current_user.id)
    except ScanNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    except ScanForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _scan_to_out(scan)
