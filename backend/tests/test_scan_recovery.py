import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.db.models.scan import Scan
from app.main import recover_stuck_scans, app


@pytest.mark.asyncio
async def test_recover_dispatches_pending_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="pending")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_called_once_with(scan.id)


@pytest.mark.asyncio
async def test_recover_dispatches_running_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="running")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_called_once_with(scan.id)


@pytest.mark.asyncio
async def test_recover_resets_running_to_pending(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="running")
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with patch("app.main.run_scan_task"):
        await recover_stuck_scans(db_session)

    await db_session.refresh(scan)
    assert scan.status == "pending"


@pytest.mark.asyncio
async def test_recover_ignores_completed_scans(db_session, registered_user):
    scan = Scan(user_id=registered_user["id"], url="https://example.com", status="completed")
    db_session.add(scan)
    await db_session.commit()

    with patch("app.main.run_scan_task") as mock_task:
        await recover_stuck_scans(db_session)
        mock_task.delay.assert_not_called()
