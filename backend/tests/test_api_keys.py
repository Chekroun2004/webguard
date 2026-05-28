"""Tests for /api-keys CRUD + X-API-Key authentication."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.audit_event import AuditEvent

API_KEYS = "/api/v1/api-keys"
ME = "/api/v1/auth/me"
REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _user_b():
    return {"email": "userb@test.com", "password": "passwordb"}


async def _login_user_b(client: AsyncClient) -> dict:
    await client.post(REG, json=_user_b())
    resp = await client.post(LOGIN, json=_user_b())
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestApiKeyCreate:
    async def test_create_returns_plaintext_once(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        resp = await client.post(API_KEYS, json={"name": "ci-bot"}, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "ci-bot"
        assert body["key"].startswith("wgk_")
        assert len(body["key"]) > 30
        assert body["prefix"].startswith("wgk_")
        # Re-listing must NOT expose the plaintext
        listed = (await client.get(API_KEYS, headers=auth_headers)).json()
        assert "key" not in listed[0]
        assert listed[0]["prefix"] == body["prefix"]

        events = (
            await db_session.execute(
                select(AuditEvent).where(AuditEvent.action == "api_key.create")
            )
        ).scalars().all()
        assert len(events) == 1 and events[0].status == "success"

    async def test_list_isolates_users(self, client: AsyncClient, auth_headers: dict):
        await client.post(API_KEYS, json={"name": "mine"}, headers=auth_headers)
        headers_b = await _login_user_b(client)
        resp = await client.get(API_KEYS, headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []


class TestApiKeyAuth:
    async def test_valid_key_authenticates_via_header(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await client.post(API_KEYS, json={"name": "k"}, headers=auth_headers)).json()
        # Drop the Bearer header — authenticate solely via X-API-Key
        resp = await client.get(ME, headers={"X-API-Key": created["key"]})
        assert resp.status_code == 200
        assert resp.json()["email"] == "tester@example.com"

    async def test_unknown_key_returns_401(self, client: AsyncClient):
        resp = await client.get(ME, headers={"X-API-Key": "wgk_definitely-not-real"})
        assert resp.status_code == 401

    async def test_malformed_key_returns_401(self, client: AsyncClient):
        # No wgk_ prefix → resolve() returns None
        resp = await client.get(ME, headers={"X-API-Key": "anything-without-prefix"})
        assert resp.status_code == 401


class TestApiKeyRevoke:
    async def test_revoke_blocks_subsequent_auth(self, client: AsyncClient, auth_headers: dict):
        created = (await client.post(API_KEYS, json={"name": "k"}, headers=auth_headers)).json()
        # Works before revoke
        assert (await client.get(ME, headers={"X-API-Key": created["key"]})).status_code == 200

        revoke = await client.delete(f"{API_KEYS}/{created['id']}", headers=auth_headers)
        assert revoke.status_code == 204

        # Same key now rejected
        resp = await client.get(ME, headers={"X-API-Key": created["key"]})
        assert resp.status_code == 401

        # Listing still shows the entry but with revoked_at populated
        listed = (await client.get(API_KEYS, headers=auth_headers)).json()
        assert listed[0]["revoked_at"] is not None

    async def test_revoke_other_user_returns_403(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        created = (await client.post(API_KEYS, json={"name": "k"}, headers=auth_headers)).json()
        headers_b = await _login_user_b(client)
        resp = await client.delete(f"{API_KEYS}/{created['id']}", headers=headers_b)
        assert resp.status_code == 403

        events = (
            await db_session.execute(
                select(AuditEvent).where(AuditEvent.action == "api_key.revoke")
            )
        ).scalars().all()
        assert len(events) == 1 and events[0].status == "failure"
