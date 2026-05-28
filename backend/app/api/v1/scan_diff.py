"""
Scan diff route — compare two scans of the same URL.

GET /scans/diff?old={id1}&new={id2}          →  JSON diff
GET /scans/diff/report.pdf?old={id1}&new={id2}  →  PDF diff download
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services.scan import ScanForbiddenError, ScanNotFoundError
from app.services.scan_diff import ScanDiffService, ScanUrlMismatchError

router = APIRouter(prefix="/scans", tags=["scans"])

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


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


def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y %H:%M")
    return str(dt)


@router.get("/diff/report.pdf")
async def get_diff_pdf_report(
    old: int = Query(..., description="ID of the older scan"),
    new: int = Query(..., description="ID of the newer scan"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
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

    old_info = result["old_scan"]
    new_info = result["new_scan"]

    diff_data = {
        "url": str(old_info["url"]).rstrip("/"),
        "old_scan": {**old_info, "created_at_str": _fmt_dt(old_info["created_at"])},
        "new_scan": {**new_info, "created_at_str": _fmt_dt(new_info["created_at"])},
        "added": [_vuln_out(v) for v in result["added"]],
        "removed": [_vuln_out(v) for v in result["removed"]],
        "unchanged": [_vuln_out(v) for v in result["unchanged"]],
    }

    generated_date = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    template = _jinja_env.get_template("diff_report.html")
    html_content = template.render(diff=diff_data, generated_date=generated_date)
    pdf_bytes = HTML(string=html_content).write_pdf()

    filename = f"webguard-diff-{old}-vs-{new}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
