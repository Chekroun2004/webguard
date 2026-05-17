"""
Unit tests for the Celery scan task.

Strategy: call execute_scan() (the async inner function) directly with a test DB session,
bypassing the Celery broker entirely. This lets us run tasks in-process with SQLite.

We mock the SCANNERS list in the tasks module so no real HTTP calls are made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models.scan import Scan, Vulnerability
from app.db.models.user import User
from app.scanners.base import Finding
from app.workers.tasks.scan import execute_scan

# ── Helpers ───────────────────────────────────────────────────────────────────

_SCANNERS_PATH = "app.workers.tasks.scan.SCANNERS"


def _make_scanner_cls(findings: list) -> MagicMock:
    """Return a mock scanner class whose instance.scan() returns findings."""
    instance = MagicMock()
    instance.scan = AsyncMock(return_value=findings)
    cls = MagicMock(return_value=instance)
    return cls


async def _create_pending_scan(engine, email: str = "task@test.com") -> tuple:
    """Insert a user + pending scan; return (session_factory, scan_id)."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        user = User(email=email, password_hash="x", is_active=True, role="user")
        session.add(user)
        await session.flush()
        scan = Scan(user_id=user.id, url="https://example.com", status="pending")
        session.add(scan)
        await session.commit()
        scan_id = scan.id
    return session_factory, scan_id


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestExecuteScan:
    async def test_marks_scan_as_completed(self, engine):
        session_factory, scan_id = await _create_pending_scan(engine, "task1@test.com")

        async with session_factory() as session:
            with patch(_SCANNERS_PATH, [_make_scanner_cls([])]):
                await execute_scan(scan_id, session)
            await session.commit()

        async with session_factory() as session:
            scan = await session.get(Scan, scan_id)
            assert scan.status == "completed"
            assert scan.finished_at is not None

    async def test_saves_findings_as_vulnerabilities(self, engine):
        session_factory, scan_id = await _create_pending_scan(engine, "task2@test.com")

        findings = [
            Finding(
                name="Missing CSP",
                severity="high",
                description="No CSP header",
                recommendation="Add CSP",
            ),
            Finding(
                name="Missing HSTS",
                severity="high",
                description="No HSTS header",
                recommendation="Add HSTS",
            ),
        ]

        async with session_factory() as session:
            with patch(_SCANNERS_PATH, [_make_scanner_cls(findings)]):
                await execute_scan(scan_id, session)
            await session.commit()

        async with session_factory() as session:
            result = await session.execute(
                select(Vulnerability).where(Vulnerability.scan_id == scan_id)
            )
            vulns = result.scalars().all()
            assert len(vulns) == 2
            names = {v.name for v in vulns}
            assert names == {"Missing CSP", "Missing HSTS"}

    async def test_marks_scan_as_failed_on_scanner_error(self, engine):
        session_factory, scan_id = await _create_pending_scan(engine, "task3@test.com")

        failing_instance = MagicMock()
        failing_instance.scan = AsyncMock(side_effect=Exception("Network error"))
        failing_cls = MagicMock(return_value=failing_instance)

        async with session_factory() as session:
            with patch(_SCANNERS_PATH, [failing_cls]):
                await execute_scan(scan_id, session)
            await session.commit()

        async with session_factory() as session:
            scan = await session.get(Scan, scan_id)
            assert scan.status == "failed"

    async def test_sets_status_to_running_before_scanning(self, engine):
        """Scan status must be 'running' while the scanner executes."""
        session_factory, scan_id = await _create_pending_scan(engine, "task4@test.com")
        observed_statuses: list[str] = []

        async def fake_scan(url, config):
            async with session_factory() as s:
                scan = await s.get(Scan, scan_id)
                observed_statuses.append(scan.status)
            return []

        spy_instance = MagicMock()
        spy_instance.scan = AsyncMock(side_effect=fake_scan)
        spy_cls = MagicMock(return_value=spy_instance)

        async with session_factory() as session:
            with patch(_SCANNERS_PATH, [spy_cls]):
                await execute_scan(scan_id, session)
            await session.commit()

        assert "running" in observed_statuses
