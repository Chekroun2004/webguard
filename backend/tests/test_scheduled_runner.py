"""Tests for the run_due_scheduled_scans Celery Beat task."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.domain import DomainOwnership
from app.db.models.scan import Scan
from app.db.models.scheduled_scan import ScheduledScan
from app.db.models.user import User


def _as_aware(dt: datetime) -> datetime:
    """SQLite strips tz on round-trip; normalize for comparisons."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


@pytest.fixture
async def user_with_verified_domain(db_session: AsyncSession) -> User:
    user = User(
        email="sched@test.com",
        password_hash="hashed",
        is_active=True,
        role="user",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        DomainOwnership(
            user_id=user.id,
            domain="example.com",
            verification_method="file",
            verification_token="x" * 64,
            is_verified=True,
            verified_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    return user


class TestHelpers:
    async def test_is_domain_verified_true(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks.scheduled import _is_domain_verified

        assert (
            await _is_domain_verified(
                db_session, user_with_verified_domain.id, "https://example.com/path"
            )
            is True
        )

    async def test_is_domain_verified_false_when_unverified(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks.scheduled import _is_domain_verified

        # Same user, different (unregistered) domain
        assert (
            await _is_domain_verified(
                db_session,
                user_with_verified_domain.id,
                "https://other.com",
            )
            is False
        )

    async def test_previous_still_running_returns_false_when_no_last_run(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks.scheduled import _previous_still_running

        sched = ScheduledScan(
            user_id=user_with_verified_domain.id,
            url="https://example.com",
            cron_expression="0 9 * * *",
            is_active=True,
            next_run_at=datetime.now(UTC),
            last_run_at=None,
        )
        db_session.add(sched)
        await db_session.flush()
        assert await _previous_still_running(db_session, sched) is False

    async def test_previous_still_running_true_when_scan_running(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks.scheduled import _previous_still_running

        last_run = datetime.now(UTC) - timedelta(minutes=2)
        sched = ScheduledScan(
            user_id=user_with_verified_domain.id,
            url="https://example.com",
            cron_expression="0 9 * * *",
            is_active=True,
            next_run_at=datetime.now(UTC),
            last_run_at=last_run,
        )
        db_session.add(sched)
        # A scan that's still running, created after last_run_at
        db_session.add(
            Scan(
                user_id=user_with_verified_domain.id,
                url="https://example.com",
                status="running",
                created_at=last_run + timedelta(seconds=1),
            )
        )
        await db_session.commit()
        assert await _previous_still_running(db_session, sched) is True


class TestRunDueScheduledScans:
    async def test_triggers_scan_when_due(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks import scheduled as mod

        past = datetime.now(UTC) - timedelta(minutes=1)
        sched = ScheduledScan(
            user_id=user_with_verified_domain.id,
            url="https://example.com",
            cron_expression="*/5 * * * *",
            is_active=True,
            next_run_at=past,
            last_run_at=None,
        )
        db_session.add(sched)
        await db_session.commit()

        called = []

        def fake_delay(scan_id: int) -> None:
            called.append(scan_id)

        with patch.object(mod, "run_scan_task") as mock_task:
            mock_task.delay = fake_delay
            result = await mod._run_due_scheduled_scans(db_session)

        assert result["triggered"] == 1
        assert result["skipped_unverified"] == 0
        assert result["skipped_overlap"] == 0
        assert len(called) == 1

        await db_session.refresh(sched)
        assert sched.last_run_at is not None
        assert _as_aware(sched.next_run_at) > datetime.now(UTC) - timedelta(seconds=5)

    async def test_skips_and_disables_when_domain_unverified(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks import scheduled as mod

        # Add a schedule on an unrelated (unverified) domain
        past = datetime.now(UTC) - timedelta(minutes=1)
        sched = ScheduledScan(
            user_id=user_with_verified_domain.id,
            url="https://other.com",
            cron_expression="*/5 * * * *",
            is_active=True,
            next_run_at=past,
            last_run_at=None,
        )
        db_session.add(sched)
        await db_session.commit()

        with patch.object(mod, "run_scan_task") as mock_task:
            mock_task.delay = lambda _id: None
            result = await mod._run_due_scheduled_scans(db_session)

        assert result["skipped_unverified"] == 1
        assert result["triggered"] == 0
        await db_session.refresh(sched)
        assert sched.is_active is False

    async def test_skips_when_previous_running(
        self, db_session: AsyncSession, user_with_verified_domain: User
    ):
        from app.workers.tasks import scheduled as mod

        last_run = datetime.now(UTC) - timedelta(minutes=5)
        past = datetime.now(UTC) - timedelta(minutes=1)
        sched = ScheduledScan(
            user_id=user_with_verified_domain.id,
            url="https://example.com",
            cron_expression="*/5 * * * *",
            is_active=True,
            next_run_at=past,
            last_run_at=last_run,
        )
        db_session.add(sched)
        db_session.add(
            Scan(
                user_id=user_with_verified_domain.id,
                url="https://example.com",
                status="running",
                created_at=last_run + timedelta(seconds=1),
            )
        )
        await db_session.commit()

        original_next_run = _as_aware(sched.next_run_at)
        called = []

        with patch.object(mod, "run_scan_task") as mock_task:
            mock_task.delay = lambda scan_id: called.append(scan_id)
            result = await mod._run_due_scheduled_scans(db_session)

        assert result["skipped_overlap"] == 1
        assert result["triggered"] == 0
        assert called == []
        await db_session.refresh(sched)
        assert _as_aware(sched.next_run_at) > original_next_run  # bumped forward
