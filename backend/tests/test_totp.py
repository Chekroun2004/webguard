"""Tests for /auth/totp routes + two-step login."""

from __future__ import annotations

import pyotp
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.audit_event import AuditEvent

REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGIN_TOTP = "/api/v1/auth/login/totp"
STATUS = "/api/v1/auth/totp/status"
ENROLL = "/api/v1/auth/totp/enroll"
CONFIRM = "/api/v1/auth/totp/confirm"
DISABLE = "/api/v1/auth/totp/disable"

USER = {"email": "tester@example.com", "password": "password123"}


def _secret_from_uri(uri: str) -> str:
    # otpauth://totp/...?secret=XXX&issuer=...
    return uri.split("secret=", 1)[1].split("&", 1)[0]


def _code(secret: str) -> str:
    return pyotp.TOTP(secret).now()


class TestTotpStatus:
    async def test_default_is_disabled(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(STATUS, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"enabled": False, "pending_setup": False}

    async def test_pending_after_enroll(self, client: AsyncClient, auth_headers: dict):
        await client.post(ENROLL, headers=auth_headers)
        resp = await client.get(STATUS, headers=auth_headers)
        assert resp.json() == {"enabled": False, "pending_setup": True}


class TestEnrollConfirm:
    async def test_enroll_returns_secret_and_uri(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(ENROLL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["secret"]) >= 16
        assert body["otpauth_uri"].startswith("otpauth://totp/")
        assert "issuer=WebGuard" in body["otpauth_uri"]

    async def test_confirm_with_valid_code_enables(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        enroll = (await client.post(ENROLL, headers=auth_headers)).json()
        secret = enroll["secret"]

        resp = await client.post(CONFIRM, json={"code": _code(secret)}, headers=auth_headers)
        assert resp.status_code == 204

        status_body = (await client.get(STATUS, headers=auth_headers)).json()
        assert status_body == {"enabled": True, "pending_setup": False}

        events = (
            (await db_session.execute(select(AuditEvent).where(AuditEvent.action == "totp.enable")))
            .scalars()
            .all()
        )
        assert len(events) == 1 and events[0].status == "success"

    async def test_confirm_with_invalid_code_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(ENROLL, headers=auth_headers)
        resp = await client.post(CONFIRM, json={"code": "000000"}, headers=auth_headers)
        assert resp.status_code == 401

    async def test_enroll_blocked_when_already_enabled(
        self, client: AsyncClient, auth_headers: dict
    ):
        enroll = (await client.post(ENROLL, headers=auth_headers)).json()
        await client.post(CONFIRM, json={"code": _code(enroll["secret"])}, headers=auth_headers)
        resp = await client.post(ENROLL, headers=auth_headers)
        assert resp.status_code == 409


class TestDisable:
    async def test_disable_with_valid_code(self, client: AsyncClient, auth_headers: dict):
        enroll = (await client.post(ENROLL, headers=auth_headers)).json()
        secret = enroll["secret"]
        await client.post(CONFIRM, json={"code": _code(secret)}, headers=auth_headers)

        resp = await client.post(DISABLE, json={"code": _code(secret)}, headers=auth_headers)
        assert resp.status_code == 204

        status_body = (await client.get(STATUS, headers=auth_headers)).json()
        assert status_body == {"enabled": False, "pending_setup": False}

    async def test_disable_without_enrollment_fails(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(DISABLE, json={"code": "123456"}, headers=auth_headers)
        assert resp.status_code == 400


class TestTwoStepLogin:
    async def test_login_without_totp_returns_tokens(self, client: AsyncClient):
        await client.post(REG, json=USER)
        resp = await client.post(LOGIN, json=USER)
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] is not None
        assert body["refresh_token"] is not None
        assert body["totp_required"] is False
        assert body["pending_token"] is None

    async def test_login_with_totp_returns_pending(self, client: AsyncClient, auth_headers: dict):
        # Enroll + confirm 2FA for the user already created by auth_headers fixture
        enroll = (await client.post(ENROLL, headers=auth_headers)).json()
        secret = enroll["secret"]
        await client.post(CONFIRM, json={"code": _code(secret)}, headers=auth_headers)

        # First login step → expects pending challenge
        resp = await client.post(LOGIN, json=USER)
        assert resp.status_code == 200
        body = resp.json()
        assert body["totp_required"] is True
        assert body["pending_token"] is not None
        assert body["access_token"] is None

        # Second step → verify code
        resp2 = await client.post(
            LOGIN_TOTP,
            json={"pending_token": body["pending_token"], "code": _code(secret)},
        )
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["access_token"] is not None
        assert body2["refresh_token"] is not None

    async def test_login_totp_invalid_code_rejected(self, client: AsyncClient, auth_headers: dict):
        enroll = (await client.post(ENROLL, headers=auth_headers)).json()
        await client.post(CONFIRM, json={"code": _code(enroll["secret"])}, headers=auth_headers)
        login_body = (await client.post(LOGIN, json=USER)).json()
        resp = await client.post(
            LOGIN_TOTP,
            json={"pending_token": login_body["pending_token"], "code": "000000"},
        )
        assert resp.status_code == 401
