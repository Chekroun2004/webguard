"""
Scan diff route — compare two scans of the same URL.

GET /scans/diff?old={id1}&new={id2}  →  {old_scan, new_scan, added, removed, unchanged}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services.scan import ScanForbiddenError, ScanNotFoundError
from app.services.scan_diff import ScanDiffService, ScanUrlMismatchError

router = APIRouter(prefix="/scans", tags=["scans"])


def _vuln_out(v) -> dict:
    return {
        "id": v.id,
        "name": v.name,
        "severity": v.severity,
        "description": v.description,
        "recommendation": v.recommendation,
        "evidence": v.evidence or "",
    }


@router.get("/diff")
async def diff_scans(
    old: int = Query(..., description="ID of the older scan"),
    new: int = Query(..., description="ID of the newer scan"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    service = ScanDiffService(db)
    try:
        result = await service.diff(old, new, current_user.id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from exc
    except ScanForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    except ScanUrlMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot diff scans of different URLs",
        ) from exc

    return {
        "old_scan": result["old_scan"],
        "new_scan": result["new_scan"],
        "added": [_vuln_out(v) for v in result["added"]],
        "removed": [_vuln_out(v) for v in result["removed"]],
        "unchanged": [_vuln_out(v) for v in result["unchanged"]],
    }
