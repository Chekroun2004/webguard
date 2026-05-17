"""
Report routes.

GET /scans/{id}/report      → JSON report
GET /scans/{id}/report.pdf  → PDF download
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.api.deps import get_current_user
from app.db.models.scan import Scan, Vulnerability
from app.db.models.user import User
from app.db.session import get_db
from app.services.report import generate_json_report
from app.services.scan import ScanForbiddenError, ScanNotFoundError, ScanService

router = APIRouter(prefix="/scans", tags=["reports"])

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


async def _get_scan_and_findings(
    scan_id: int,
    user: User,
    session: AsyncSession,
) -> tuple[Scan, list[Vulnerability]]:
    """Shared helper: fetch scan (checking ownership) + its findings."""
    try:
        scan = await ScanService(session).get_scan(scan_id, user.id)
    except ScanNotFoundError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan not found") from exc
    except ScanForbiddenError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Access forbidden") from exc

    result = await session.execute(select(Vulnerability).where(Vulnerability.scan_id == scan_id))
    findings = list(result.scalars().all())
    return scan, findings


@router.get("/{scan_id}/report")
async def get_json_report(
    scan_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    scan, findings = await _get_scan_and_findings(scan_id, user, session)
    return generate_json_report(scan, findings)


@router.get("/{scan_id}/report.pdf")
async def get_pdf_report(
    scan_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    scan, findings = await _get_scan_and_findings(scan_id, user, session)
    report = generate_json_report(scan, findings)

    generated_date = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    template = _jinja_env.get_template("report.html")
    html_content = template.render(report=report, generated_date=generated_date)

    pdf_bytes = HTML(string=html_content).write_pdf()

    filename = f"webguard-report-{scan_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
