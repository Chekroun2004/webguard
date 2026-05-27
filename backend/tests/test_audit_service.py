"""Tests for AuditService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.audit import ACTIONS, AuditService


@pytest.mark.asyncio
async def test_log_creates_event_with_request_context(db_session, registered_user):
    request = MagicMock()
    request.client.host = "10.1.2.3"
    request.headers = {"user-agent": "Mozilla/5.0"}

    event = await AuditService(db_session).log(
        registered_user["id"], "scan.create",
        target_type="scan", target_id=1, request=request,
    )
    assert event is not None
    assert event.ip == "10.1.2.3"
    assert event.user_agent == "Mozilla/5.0"
    assert event.status == "success"
    assert event.action == "scan.create"


@pytest.mark.asyncio
async def test_log_handles_missing_request(db_session, registered_user):
    event = await AuditService(db_session).log(registered_user["id"], "totp.enable")
    assert event is not None
    assert event.ip is None
    assert event.user_agent is None
    assert event.status == "success"


@pytest.mark.asyncio
async def test_log_truncates_long_user_agent(db_session, registered_user):
    request = MagicMock()
    request.client.host = "1.1.1.1"
    request.headers = {"user-agent": "x" * 1000}

    event = await AuditService(db_session).log(
        registered_user["id"], "scan.create", request=request
    )
    assert event is not None
    assert len(event.user_agent) == 512


@pytest.mark.asyncio
async def test_log_records_failure_status(db_session, registered_user):
    event = await AuditService(db_session).log(
        registered_user["id"], "webhook.delete",
        target_type="webhook", target_id=42, status="failure",
    )
    assert event is not None
    assert event.status == "failure"


@pytest.mark.asyncio
async def test_log_rejects_unknown_action(db_session, registered_user):
    with pytest.raises(ValueError, match="unknown audit action"):
        await AuditService(db_session).log(registered_user["id"], "not.a.real.action")


@pytest.mark.asyncio
async def test_log_swallows_db_errors_returning_none(db_session, registered_user, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr("app.services.audit.create_audit_event", boom)

    result = await AuditService(db_session).log(registered_user["id"], "scan.create")
    assert result is None


def test_actions_set_size_matches_spec():
    assert len(ACTIONS) == 14
