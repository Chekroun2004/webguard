"""
Scan repository — thin async DB layer (no business logic here).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.scan import Scan, Vulnerability
from app.scanners.base import Finding


async def create_scan(
    db: AsyncSession,
    user_id: int,
    url: str,
    findings: list[Finding],
    status: str = "completed",
) -> Scan:
    from datetime import datetime, timezone

    scan = Scan(
        user_id=user_id,
        url=url,
        status=status,
        finished_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    await db.flush()  # get scan.id

    for f in findings:
        vuln = Vulnerability(
            scan_id=scan.id,
            name=f.name,
            severity=f.severity,
            description=f.description,
            recommendation=f.recommendation,
            evidence=f.evidence,
        )
        db.add(vuln)

    await db.flush()
    await db.refresh(scan, ["vulnerabilities"])
    return scan


async def get_scan_by_id(db: AsyncSession, scan_id: int) -> Scan | None:
    result = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.vulnerabilities))
    )
    return result.scalar_one_or_none()


async def list_scans_for_user(db: AsyncSession, user_id: int) -> list[Scan]:
    result = await db.execute(
        select(Scan)
        .where(Scan.user_id == user_id)
        .options(selectinload(Scan.vulnerabilities))
        .order_by(Scan.created_at.desc())
    )
    return list(result.scalars().all())
