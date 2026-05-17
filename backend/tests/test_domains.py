"""
Tests for domain ownership verification — Étape 5.

POST   /api/v1/domains              → create verification record (201)
GET    /api/v1/domains              → list user's domains
GET    /api/v1/domains/{id}         → domain detail
POST   /api/v1/domains/{id}/verify  → trigger file or DNS check
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


class TestDomainRegister:
    async def test_creates_domain_record(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/domains",
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

    async def test_default_method_is_file(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/domains",
            json={"domain": "example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["verification_method"] == "file"

    async def test_normalizes_domain_strips_scheme_and_path(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/domains",
            json={"domain": "https://EXAMPLE.com/some/path"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["domain"] == "example.com"

    async def test_duplicate_domain_returns_409(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/domains", json={"domain": "example.com"}, headers=auth_headers)
        resp = await client.post("/api/v1/domains", json={"domain": "example.com"}, headers=auth_headers)
        assert resp.status_code == 409

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/domains", json={"domain": "example.com"})
        assert resp.status_code == 401

    async def test_dns_method_accepted(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/domains",
            json={"domain": "example.com", "method": "dns"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["verification_method"] == "dns"

    async def test_invalid_method_returns_422(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/domains",
            json={"domain": "example.com", "method": "ftp"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestDomainList:
    async def test_returns_user_domains(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/domains", json={"domain": "a.com"}, headers=auth_headers)
        await client.post("/api/v1/domains", json={"domain": "b.com"}, headers=auth_headers)
        resp = await client.get("/api/v1/domains", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_user_sees_only_their_domains(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/domains", json={"domain": "a.com"}, headers=auth_headers)
        await client.post("/api/v1/auth/register", json={"email": "b@test.com", "password": "pass1234"})
        login_b = await client.post("/api/v1/auth/login", json={"email": "b@test.com", "password": "pass1234"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        resp = await client.get("/api/v1/domains", headers=headers_b)
        assert resp.json() == []

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/domains")
        assert resp.status_code == 401


class TestDomainGet:
    async def test_returns_domain_by_id(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post("/api/v1/domains", json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        resp = await client.get(f"/api/v1/domains/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["domain"] == "example.com"

    async def test_404_for_unknown_domain(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/domains/9999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_for_other_users_domain(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post("/api/v1/domains", json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        await client.post("/api/v1/auth/register", json={"email": "b@test.com", "password": "pass1234"})
        login_b = await client.post("/api/v1/auth/login", json={"email": "b@test.com", "password": "pass1234"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        resp = await client.get(f"/api/v1/domains/{created['id']}", headers=headers_b)
        assert resp.status_code == 403


class TestDomainVerify:
    async def test_file_verification_success(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = token

        mock_get = AsyncMock(return_value=mock_resp)
        mock_session = AsyncMock()
        mock_session.get = mock_get
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.domain.httpx.AsyncClient", return_value=mock_cm):
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_verified"] is True
        assert data["verified_at"] is not None

    async def test_file_verification_wrong_token_returns_400(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
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

        with patch("app.services.domain.httpx.AsyncClient", return_value=mock_cm):
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_file_verification_404_returns_400(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
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

        with patch("app.services.domain.httpx.AsyncClient", return_value=mock_cm):
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_dns_verification_success(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
                json={"domain": "example.com", "method": "dns"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]

        mock_rdata = AsyncMock()
        mock_rdata.strings = [f"webguard-verify={token}".encode()]

        with patch("app.services.domain.dns.asyncresolver.resolve", AsyncMock(return_value=[mock_rdata])):
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    async def test_dns_verification_wrong_record_returns_400(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
                json={"domain": "example.com", "method": "dns"},
                headers=auth_headers,
            )
        ).json()

        mock_rdata = AsyncMock()
        mock_rdata.strings = [b"webguard-verify=wrong-token"]

        with patch("app.services.domain.dns.asyncresolver.resolve", AsyncMock(return_value=[mock_rdata])):
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 400

    async def test_already_verified_idempotent(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post(
                "/api/v1/domains",
                json={"domain": "example.com", "method": "file"},
                headers=auth_headers,
            )
        ).json()
        token = created["verification_token"]

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = token
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_resp)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.domain.httpx.AsyncClient", return_value=mock_cm):
            await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)
            resp = await client.post(f"/api/v1/domains/{created['id']}/verify", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    async def test_verify_requires_auth(self, client: AsyncClient, auth_headers: dict):
        created = (
            await client.post("/api/v1/domains", json={"domain": "example.com"}, headers=auth_headers)
        ).json()
        resp = await client.post(f"/api/v1/domains/{created['id']}/verify")
        assert resp.status_code == 401
