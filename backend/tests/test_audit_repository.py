"""Tests for AuditEvent repository."""

from __future__ import annotations

import pytest

from app.repositories.audit import create_audit_event, list_audit_events


@pytest.mark.asyncio
async def test_create_audit_event_persists_row(db_session, registered_user):
    event = await create_audit_event(
        db_session,
        user_id=registered_user["id"],
        action="scan.create",
        target_type="scan",
        target_id=42,
        status="success",
        ip="127.0.0.1",
        user_agent="curl/8.0",
    )
    await db_session.flush()
    assert event.id is not None
    assert event.action == "scan.create"
    assert event.target_type == "scan"
    assert event.target_id == 42
    assert event.status == "success"


@pytest.mark.asyncio
async def test_list_audit_events_paginates(db_session, registered_user):
    uid = registered_user["id"]
    for _ in range(5):
        await create_audit_event(
            db_session,
            user_id=uid,
            action="scan.create",
            target_type=None,
            target_id=None,
            status="success",
            ip=None,
            user_agent=None,
        )
    await db_session.flush()

    items, total = await list_audit_events(db_session, user_id=uid, page=1, page_size=2)
    assert total == 5
    assert len(items) == 2


@pytest.mark.asyncio
async def test_list_audit_events_filters_by_action(db_session, registered_user):
    uid = registered_user["id"]
    for action in ("scan.create", "scan.create", "webhook.delete"):
        await create_audit_event(
            db_session,
            user_id=uid,
            action=action,
            target_type=None,
            target_id=None,
            status="success",
            ip=None,
            user_agent=None,
        )
    await db_session.flush()

    items, total = await list_audit_events(
        db_session, user_id=uid, page=1, page_size=10, action="scan.create"
    )
    assert total == 2
    assert all(e.action == "scan.create" for e in items)


@pytest.mark.asyncio
async def test_list_audit_events_filters_by_status(db_session, registered_user):
    uid = registered_user["id"]
    await create_audit_event(
        db_session,
        user_id=uid,
        action="scan.create",
        target_type=None,
        target_id=None,
        status="success",
        ip=None,
        user_agent=None,
    )
    await create_audit_event(
        db_session,
        user_id=uid,
        action="scan.create",
        target_type=None,
        target_id=None,
        status="failure",
        ip=None,
        user_agent=None,
    )
    await db_session.flush()

    items, total = await list_audit_events(
        db_session, user_id=uid, page=1, page_size=10, status="failure"
    )
    assert total == 1


@pytest.mark.asyncio
async def test_list_audit_events_scoped_to_user(db_session, registered_user):
    from app.db.models.user import User

    other = User(email="other@test.com", password_hash="x", is_active=True, role="user")
    db_session.add(other)
    await db_session.flush()

    await create_audit_event(
        db_session,
        user_id=registered_user["id"],
        action="scan.create",
        target_type=None,
        target_id=None,
        status="success",
        ip=None,
        user_agent=None,
    )
    await create_audit_event(
        db_session,
        user_id=other.id,
        action="scan.create",
        target_type=None,
        target_id=None,
        status="success",
        ip=None,
        user_agent=None,
    )
    await db_session.flush()

    items, total = await list_audit_events(db_session, user_id=registered_user["id"])
    assert total == 1
    assert items[0].user_id == registered_user["id"]
