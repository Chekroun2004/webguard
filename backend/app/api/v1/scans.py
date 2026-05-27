"""
Scan API routes.

POST   /scans              → 202 pending, dispatches Celery task
GET    /scans              → list user's scans
GET    /scans/{id}         → scan detail
GET    /scans/{id}/status  → {id, status}
GET    /scans/{id}/events  → SSE stream of status updates
"""

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.limiter import get_user_id_key, limiter
from app.db.models.user import User
from app.db.session import AsyncSessionLocal, get_db
from app.repositories.scan import get_scan_by_id
from app.schemas.scan import ScanCreate, ScanOut, VulnerabilityOut
from app.services.audit import AuditService
from app.services.scan import ScanForbiddenError, ScanNotFoundError, ScanService
from app.workers.tasks.scan import run_scan_task

router = APIRouter(prefix="/scans", tags=["scans"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_out(scan) -> ScanOut:
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


# ── Routes ────────────────────────────────────────────────────────────────────


async def _run_scan_in_process(scan_id: int) -> None:
    """Fallback when Celery is disabled — run the scan in the API process."""
    from app.db.session import task_session
    from app.workers.tasks.scan import execute_scan

    async with task_session() as session:
        await execute_scan(scan_id, session)
        await session.commit()


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=ScanOut)
@limiter.limit("5/hour", key_func=get_user_id_key)
async def create_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ScanCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanOut:
    service = ScanService(db)
    auth_payload = (
        body.auth_config.model_dump(mode="json") if body.auth_config is not None else None
    )
    scan = await service.create_scan(
        user_id=current_user.id,
        url=str(body.url),
        auth_config=auth_payload,
    )
    # Dispatch async task AFTER the scan row is persisted
    if settings.use_celery:
        run_scan_task.delay(scan.id)
    else:
        background_tasks.add_task(_run_scan_in_process, scan.id)
    await AuditService(db).log(
        current_user.id, "scan.create",
        target_type="scan", target_id=scan.id,
        status="success", request=request,
    )
    return _to_out(scan)


@router.get("", response_model=list[ScanOut])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScanOut]:
    service = ScanService(db)
    scans = await service.list_scans(user_id=current_user.id)
    return [_to_out(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScanOut:
    service = ScanService(db)
    try:
        scan = await service.get_scan(scan_id=scan_id, user_id=current_user.id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from exc
    except ScanForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    return _to_out(scan)


@router.get("/{scan_id}/status")
async def get_scan_status(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    service = ScanService(db)
    try:
        scan = await service.get_scan(scan_id=scan_id, user_id=current_user.id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from exc
    except ScanForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc
    return {"id": scan.id, "status": scan.status}


@router.get("/{scan_id}/events")
async def scan_events(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventSourceResponse:
    """SSE stream — emits a 'status' event every second until the scan finishes."""
    # Auth check before opening the stream
    service = ScanService(db)
    try:
        await service.get_scan(scan_id=scan_id, user_id=current_user.id)
    except ScanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from exc
    except ScanForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from exc

    async def event_generator():
        while True:
            async with AsyncSessionLocal() as fresh_db:
                scan = await get_scan_by_id(fresh_db, scan_id)

            if scan is None:
                break

            payload = json.dumps({"id": scan.id, "status": scan.status})
            yield {"event": "status", "data": payload}

            if scan.status in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
