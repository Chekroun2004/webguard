"""Tests for /api/v1/scheduled CRUD endpoints + service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

URL = "/api/v1/scheduled"
DOMAINS = "/api/v1/domains"
REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"

# Patch path for the file-verification httpx client (re-used from test_domains.py pattern).
_HTTPX = "app.services.domain.httpx.AsyncClient"


def _file_mock(token: str):
    """Return (mock_cm, mock_resp) for a successful file verification."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = token
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_resp)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm, mock_resp


async def _create_verified_domain(client: AsyncClient, headers: dict, domain: str) -> None:
    """Helper: register a domain and mark it as verified via mocked file-check."""
    created = (
        await client.post(
            DOMAINS, json={"domain": domain, "method": "file"}, headers=headers
        )
    ).json()
    token = created["verification_token"]
    mock_cm, _ = _file_mock(token)
    with patch(_HTTPX, return_value=mock_cm):
        await client.post(f"{DOMAINS}/{created['id']}/verify", headers=headers)


class TestScheduledCreate:
    async def test_creates_scheduled_scan_for_verified_domain(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        resp = await client.post(
            URL,
            json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com"
        assert data["cron_expression"] == "0 9 * * *"
        assert data["is_active"] is True
        assert data["last_run_at"] is None
        assert data["next_run_at"] is not None

    async def test_rejects_invalid_cron(self, client: AsyncClient, auth_headers: dict):
        await _create_verified_domain(client, auth_headers, "example.com")
        resp = await client.post(
            URL,
            json={"url": "https://example.com", "cron_expression": "not-a-cron"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_rejects_unverified_domain(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Register the domain but DO NOT verify it
        await client.post(
            DOMAINS, json={"domain": "unverified.com"}, headers=auth_headers
        )
        resp = await client.post(
            URL,
            json={"url": "https://unverified.com", "cron_expression": "0 9 * * *"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    async def test_rejects_no_domain_registered(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            URL,
            json={"url": "https://nothing-here.com", "cron_expression": "0 9 * * *"},
            headers=auth_headers,
        )
        assert resp.status_code == 403


def _user_b():
    return {"email": "userb@test.com", "password": "passwordb"}


async def _login_user_b(client: AsyncClient) -> dict:
    await client.post(REG, json=_user_b())
    resp = await client.post(LOGIN, json=_user_b())
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestScheduledList:
    async def test_list_returns_user_schedules(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        await client.post(
            URL,
            json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
            headers=auth_headers,
        )
        resp = await client.get(URL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["url"] == "https://example.com"

    async def test_list_returns_only_owned(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        await client.post(
            URL,
            json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
            headers=auth_headers,
        )
        headers_b = await _login_user_b(client)
        resp = await client.get(URL, headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []


class TestScheduledGet:
    async def test_returns_404_for_unknown(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(f"{URL}/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_403_for_other_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        headers_b = await _login_user_b(client)
        resp = await client.get(f"{URL}/{created['id']}", headers=headers_b)
        assert resp.status_code == 403


class TestScheduledUpdate:
    async def test_patch_recomputes_next_run_at(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        original_next = created["next_run_at"]

        resp = await client.patch(
            f"{URL}/{created['id']}",
            json={"cron_expression": "0 12 * * *"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cron_expression"] == "0 12 * * *"
        assert data["next_run_at"] != original_next

    async def test_patch_toggle_is_active(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        resp = await client.patch(
            f"{URL}/{created['id']}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_patch_invalid_cron_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        resp = await client.patch(
            f"{URL}/{created['id']}",
            json={"cron_expression": "garbage"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_patch_403_for_other_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        headers_b = await _login_user_b(client)
        resp = await client.patch(
            f"{URL}/{created['id']}",
            json={"is_active": False},
            headers=headers_b,
        )
        assert resp.status_code == 403


class TestScheduledDelete:
    async def test_delete_returns_204(self, client: AsyncClient, auth_headers: dict):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        resp = await client.delete(f"{URL}/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204
        # Verify gone
        get_resp = await client.get(f"{URL}/{created['id']}", headers=auth_headers)
        assert get_resp.status_code == 404

    async def test_delete_403_for_other_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_verified_domain(client, auth_headers, "example.com")
        created = (
            await client.post(
                URL,
                json={"url": "https://example.com", "cron_expression": "0 9 * * *"},
                headers=auth_headers,
            )
        ).json()
        headers_b = await _login_user_b(client)
        resp = await client.delete(f"{URL}/{created['id']}", headers=headers_b)
        assert resp.status_code == 403
