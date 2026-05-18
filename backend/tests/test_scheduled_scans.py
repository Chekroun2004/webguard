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
