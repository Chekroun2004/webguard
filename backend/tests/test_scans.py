"""
Integration tests for POST /api/v1/scans and GET /api/v1/scans/{id}.

Strategy: mock HeadersScanner._fetch so no real HTTP calls happen during tests.
All scan operations run synchronously (no Celery yet — that's Étape 4).
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


SAFE_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=()",
}

RISKY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    # Missing CSP, HSTS, Referrer-Policy → should generate findings
}

MOCK_FETCH_SAFE = AsyncMock(return_value={"status": 200, "headers": SAFE_HEADERS, "body": ""})
MOCK_FETCH_RISKY = AsyncMock(return_value={"status": 200, "headers": RISKY_HEADERS, "body": ""})


class TestCreateScan:
    async def test_returns_201_with_scan_id(self, client: AsyncClient, auth_headers: dict):
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        # Pydantic AnyHttpUrl normalises to trailing slash
        assert data["url"].rstrip("/") == "https://example.com"
        assert data["status"] == "completed"

    async def test_returns_findings_list(self, client: AsyncClient, auth_headers: dict):
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_RISKY):
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://insecure.example.com"},
                headers=auth_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert isinstance(data["findings"], list)
        assert len(data["findings"]) > 0
        finding = data["findings"][0]
        assert "name" in finding
        assert "severity" in finding
        assert "description" in finding

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/scans",
            json={"url": "https://example.com"},
        )
        assert resp.status_code == 401

    async def test_rejects_invalid_url(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/scans",
            json={"url": "not-a-url"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_clean_site_has_zero_findings(self, client: AsyncClient, auth_headers: dict):
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://secure.example.com"},
                headers=auth_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["findings"] == []


class TestGetScan:
    async def test_returns_scan_by_id(self, client: AsyncClient, auth_headers: dict):
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]
        resp = await client.get(f"/api/v1/scans/{scan_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == scan_id

    async def test_returns_404_for_unknown_scan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/scans/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_403_for_other_users_scan(self, client: AsyncClient, auth_headers: dict):
        # Create scan with user A
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]

        # Register and login user B
        await client.post(
            "/api/v1/auth/register",
            json={"email": "other@example.com", "password": "password123"},
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "other@example.com", "password": "password123"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_requires_auth_for_get(self, client: AsyncClient, auth_headers: dict):
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]
        resp = await client.get(f"/api/v1/scans/{scan_id}")
        assert resp.status_code == 401


class TestListScans:
    async def test_user_sees_only_their_scans(self, client: AsyncClient, auth_headers: dict):
        # Create 2 scans for user A
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            await client.post("/api/v1/scans", json={"url": "https://a.com"}, headers=auth_headers)
            await client.post("/api/v1/scans", json={"url": "https://b.com"}, headers=auth_headers)

        # Create 1 scan for user B
        await client.post("/api/v1/auth/register", json={"email": "userb@example.com", "password": "password123"})
        login_b = await client.post("/api/v1/auth/login", json={"email": "userb@example.com", "password": "password123"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        with patch("app.scanners.headers.HeadersScanner._fetch", new=MOCK_FETCH_SAFE):
            await client.post("/api/v1/scans", json={"url": "https://c.com"}, headers=headers_b)

        # User A should only see their 2 scans
        resp = await client.get("/api/v1/scans", headers=auth_headers)
        assert resp.status_code == 200
        scans = resp.json()
        assert len(scans) == 2
        urls = {s["url"].rstrip("/") for s in scans}
        assert urls == {"https://a.com", "https://b.com"}

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/scans")
        assert resp.status_code == 401
