"""
Tests for domain ownership verification — Étape 5.

POST   /api/v1/domains              → create verification record (201)
GET    /api/v1/domains              → list user's domains
GET    /api/v1/domains/{id}         → domain detail
POST   /api/v1/domains/{id}/verify  → trigger file or DNS check
"""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.audit_event import AuditEvent

URL = "/api/v1/domains"
REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _user_b_json():
    return {"email": "b@test.com", "password": "pass1234"}


class TestDomainRegister:
    async def test_creates_domain_record(self, client: AsyncClient, auth_headers: dict, db_session):
        resp = await client.post(
            URL,
            json={"domain": "example.com", "method": "file"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["domain"] == "example.com"
        assert data["verification_method"] == "file"
        assert len(data["verification_token"]) == 64
        assert data["is_verified"] is False
        assert data["verified_at"] is None

        events = (
            (
                await db_session.execute(
                    select(AuditEvent).where(AuditEvent.action == "domain.create")
                )
            )
            .scalars()
            .all()
        )
        assert len(events) == 1 and events[0].status == "success"

    async def test_default_method_is_file(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["verification_method"] == "file"

    async def test_normalizes_domain_strips_scheme_and_path(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            URL,
            json={"domain": "https://EXAMPLE.com/some/path"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["domain"] == "example.com"

    async def test_duplicate_domain_returns_409(self, client: AsyncClient, auth_headers: dict):
        await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        resp = await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        assert resp.status_code == 409

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(URL, json={"domain": "example.com"})
        assert resp.status_code == 401

    async def test_dns_method_accepted(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            URL,
            json={"domain": "example.com", "method": "dns"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["verification_method"] == "dns"

    async def test_invalid_method_returns_422(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            URL,
            json={"domain": "example.com", "method": "ftp"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestDomainList:
    async def test_returns_user_domains(self, client: AsyncClient, auth_headers: dict):
        await client.post(URL, json={"domain": "a.com"}, headers=auth_headers)
        await client.post(URL, json={"domain": "b.com"}, headers=auth_headers)
        resp = await client.get(URL, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_user_sees_only_their_domains(self, client: AsyncClient, auth_headers: dict):
        await client.post(URL, json={"domain": "a.com"}, headers=auth_headers)
        await client.post(REG, json=_user_b_json())
        login_b = await client.post(LOGIN, json=_user_b_json())
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        resp = await client.get(URL, headers=headers_b)
        assert resp.json() == []

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(URL)
        assert resp.status_code == 401


class TestDomainGet:
    async def test_returns_domain_by_id(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        resp = await client.get(f"{URL}/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["domain"] == "example.com"

    async def test_404_for_unknown_domain(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"{URL}/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_for_other_users_domain(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        await client.post(REG, json=_user_b_json())
        login_b = await client.post(LOGIN, json=_user_b_json())
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        resp = await client.get(f"{URL}/{created['id']}", headers=headers_b)
        assert resp.status_code == 403


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


_HTTPX = "app.services.domain.httpx.AsyncClient"
_DNS = "app.services.domain.dns.asyncresolver.resolve"


class TestDomainVerify:
    async def test_file_verification_success(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]
        mock_cm, _ = _file_mock(token)

        with patch(_HTTPX, return_value=mock_cm):
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_verified"] is True
        assert data["verified_at"] is not None

    async def test_file_verification_wrong_token_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = "wrong-token-that-does-not-match"
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_resp)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch(_HTTPX, return_value=mock_cm):
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_file_verification_404_returns_400(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()

        mock_resp = AsyncMock()
        mock_resp.status_code = 404
        mock_resp.text = ""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_resp)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch(_HTTPX, return_value=mock_cm):
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_dns_verification_success(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "dns"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]
        mock_rdata = AsyncMock()
        mock_rdata.strings = [f"webguard-verify={token}".encode()]

        with patch(_DNS, AsyncMock(return_value=[mock_rdata])):
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    async def test_dns_verification_wrong_record_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "dns"},
                headers=auth_headers,
            )
        ).json()

        mock_rdata = AsyncMock()
        mock_rdata.strings = [b"webguard-verify=wrong-token"]

        with patch(_DNS, AsyncMock(return_value=[mock_rdata])):
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_already_verified_idempotent(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                URL,
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]
        mock_cm, _ = _file_mock(token)

        with patch(_HTTPX, return_value=mock_cm):
            await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)
            resp = await client.post(f"{URL}/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    async def test_verify_requires_auth(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(URL, json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        resp = await client.post(f"{URL}/{created['id']}/verify")
        assert resp.status_code == 401
