"""Tests for /api/v1/webhooks CRUD + webhook_sender service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

URL = "/api/v1/webhooks"
REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"

SLACK_URL = "https://hooks.slack.com/services/T000/B000/xxx"
DISCORD_URL = "https://discord.com/api/webhooks/123/abc"


def _user_b():
    return {"email": "userb@test.com", "password": "passwordb"}


async def _login_user_b(client: AsyncClient) -> dict:
    await client.post(REG, json=_user_b())
    resp = await client.post(LOGIN, json=_user_b())
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestWebhookCreate:
    async def test_creates_slack_webhook(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            URL,
            json={"url": SLACK_URL, "provider": "slack"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == SLACK_URL
        assert data["provider"] == "slack"
        assert data["is_active"] is True
        assert "id" in data

    async def test_creates_discord_webhook(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            URL,
            json={"url": DISCORD_URL, "provider": "discord"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["provider"] == "discord"

    async def test_rejects_unknown_provider(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            URL,
            json={"url": SLACK_URL, "provider": "telegram"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestWebhookList:
    async def test_returns_only_owned(self, client: AsyncClient, auth_headers: dict):
        await client.post(URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers)
        headers_b = await _login_user_b(client)
        resp = await client.get(URL, headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_user_webhooks(self, client: AsyncClient, auth_headers: dict):
        await client.post(URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers)
        await client.post(
            URL, json={"url": DISCORD_URL, "provider": "discord"}, headers=auth_headers
        )
        resp = await client.get(URL, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestWebhookUpdateDelete:
    async def test_patch_toggle_active(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers
            )
        ).json()
        resp = await client.patch(
            f"{URL}/{created['id']}", json={"is_active": False}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_patch_403_for_other_user(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers
            )
        ).json()
        headers_b = await _login_user_b(client)
        resp = await client.patch(
            f"{URL}/{created['id']}", json={"is_active": False}, headers=headers_b
        )
        assert resp.status_code == 403

    async def test_delete_returns_204(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers
            )
        ).json()
        resp = await client.delete(f"{URL}/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204
        list_resp = await client.get(URL, headers=auth_headers)
        assert list_resp.json() == []

    async def test_delete_404_unknown(self, client: AsyncClient, auth_headers: dict):
        resp = await client.delete(f"{URL}/99999", headers=auth_headers)
        assert resp.status_code == 404


def _httpx_mock(status_code: int = 200):
    """Build a mocked httpx.AsyncClient context manager that returns the given status."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("boom")
    )
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_resp)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm, mock_session


class TestWebhookTest:
    async def test_test_endpoint_posts_payload(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers
            )
        ).json()
        mock_cm, mock_session = _httpx_mock(200)
        with patch("app.api.v1.webhooks.httpx.AsyncClient", return_value=mock_cm):
            resp = await client.post(f"{URL}/{created['id']}/test", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"delivered": True}
        mock_session.post.assert_awaited_once()

    async def test_test_endpoint_reports_failure_silently(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (
            await client.post(
                URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers
            )
        ).json()
        mock_cm, _ = _httpx_mock(500)
        with patch("app.api.v1.webhooks.httpx.AsyncClient", return_value=mock_cm):
            resp = await client.post(f"{URL}/{created['id']}/test", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"delivered": False}


class TestWebhookSenderPayloads:
    def test_build_slack_payload_structure(self):
        from app.services.webhook_sender import build_slack_payload

        scan = MagicMock(id=42, url="https://target.example.com")
        payload = build_slack_payload(scan, [])
        assert "blocks" in payload
        assert payload["text"].startswith("WebGuard")
        assert any(
            b.get("type") == "actions" and "https://target.example.com" not in str(b)
            for b in payload["blocks"]
        )

    def test_build_discord_payload_structure(self):
        from app.services.webhook_sender import build_discord_payload

        scan = MagicMock(id=42, url="https://target.example.com")
        vuln = MagicMock(severity="high")
        payload = build_discord_payload(scan, [vuln])
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert "WebGuard" in embed["title"]
        assert embed["color"] == 0xDC2626

    def test_build_payload_rejects_unknown_provider(self):
        from app.services.webhook_sender import build_payload

        scan = MagicMock(id=1, url="https://x")
        with pytest.raises(ValueError):
            build_payload("telegram", scan, [])


class TestNotifyScanComplete:
    async def test_notify_skips_inactive_webhooks(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        from sqlalchemy import select

        from app.db.models.user import User
        from app.db.models.webhook import Webhook
        from app.services.webhook_sender import notify_scan_complete

        # Create one active + one inactive webhook for the logged-in user.
        await client.post(URL, json={"url": SLACK_URL, "provider": "slack"}, headers=auth_headers)
        inactive = (
            await client.post(
                URL, json={"url": DISCORD_URL, "provider": "discord"}, headers=auth_headers
            )
        ).json()
        await client.patch(
            f"{URL}/{inactive['id']}", json={"is_active": False}, headers=auth_headers
        )

        user = (
            await db_session.execute(select(User).where(User.email == "tester@example.com"))
        ).scalar_one()
        # Sanity: webhook rows are visible in db_session
        assert (
            (await db_session.execute(select(Webhook).where(Webhook.user_id == user.id)))
            .scalars()
            .all()
        )

        scan = MagicMock(id=7, url="https://example.com")

        mock_cm, mock_session = _httpx_mock(200)
        with patch("app.services.webhook_sender.httpx.AsyncClient", return_value=mock_cm):
            delivered = await notify_scan_complete(db_session, user.id, scan, [])

        assert delivered == 1
        assert mock_session.post.await_count == 1
