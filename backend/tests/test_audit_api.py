"""Tests for GET /api/v1/audit."""

from __future__ import annotations

import pytest

from app.db.models.user import User
from app.repositories.audit import create_audit_event


async def _seed_event(db_session, user_id, action="scan.create", status="success"):
    await create_audit_event(
        db_session,
        user_id=user_id,
        action=action,
        target_type=None,
        target_id=None,
        status=status,
        ip=None,
        user_agent=None,
    )


async def _user_a_id(db_session) -> int:
    # auth_headers registers tester@example.com — fetch its id from the DB
    from sqlalchemy import select

    res = await db_session.execute(select(User).where(User.email == "tester@example.com"))
    return res.scalar_one().id


@pytest.mark.asyncio
async def test_get_audit_requires_auth(client):
    r = await client.get("/api/v1/audit")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_audit_returns_paginated_list(client, auth_headers, db_session):
    uid = await _user_a_id(db_session)
    for _ in range(3):
        await _seed_event(db_session, uid)
    await db_session.commit()

    r = await client.get("/api/v1/audit", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert all(item["user_id"] == uid for item in body["items"])
    assert body["page"] == 1
    assert body["page_size"] == 50


@pytest.mark.asyncio
async def test_get_audit_scoped_to_current_user(client, auth_headers, db_session):
    uid_a = await _user_a_id(db_session)
    # Create user B directly
    user_b = User(email="other@test.com", password_hash="x", is_active=True, role="user")
    db_session.add(user_b)
    await db_session.flush()

    await _seed_event(db_session, uid_a)
    await _seed_event(db_session, user_b.id)
    await db_session.commit()

    r = await client.get("/api/v1/audit", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_audit_filters_by_action(client, auth_headers, db_session):
    uid = await _user_a_id(db_session)
    await _seed_event(db_session, uid, action="scan.create")
    await _seed_event(db_session, uid, action="webhook.delete")
    await db_session.commit()

    r = await client.get("/api/v1/audit?action=webhook.delete", headers=auth_headers)
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_audit_filters_by_status(client, auth_headers, db_session):
    uid = await _user_a_id(db_session)
    await _seed_event(db_session, uid, status="success")
    await _seed_event(db_session, uid, status="failure")
    await db_session.commit()

    r = await client.get("/api/v1/audit?status=failure", headers=auth_headers)
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_audit_rejects_unknown_action_filter(client, auth_headers):
    r = await client.get("/api/v1/audit?action=nope.bad", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_audit_pagination(client, auth_headers, db_session):
    uid = await _user_a_id(db_session)
    for _ in range(5):
        await _seed_event(db_session, uid)
    await db_session.commit()

    r = await client.get("/api/v1/audit?page=1&page_size=2", headers=auth_headers)
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 1 and body["page_size"] == 2

    r = await client.get("/api/v1/audit?page=3&page_size=2", headers=auth_headers)
    assert len(r.json()["items"]) == 1
