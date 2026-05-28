"""
Integration tests for scan routes — async version (Étape 4).

POST /api/v1/scans  → 202, status=pending, task dispatched
GET  /api/v1/scans  → list user's scans
GET  /api/v1/scans/{id}        → scan detail (with findings after task completes)
GET  /api/v1/scans/{id}/status → current status
GET  /api/v1/scans/{id}/events → SSE stream
"""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from app.db.models.audit_event import AuditEvent


class TestCreateScan:
    async def test_returns_202_with_pending_status(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        assert resp.status_code == 202
        data = resp.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["findings"] == []

        events = (
            (await db_session.execute(select(AuditEvent).where(AuditEvent.action == "scan.create")))
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].status == "success"
        assert events[0].target_id == resp.json()["id"]

    async def test_dispatches_celery_task_with_scan_id(
        self, client: AsyncClient, auth_headers: dict
    ):
        with patch("app.api.v1.scans.run_scan_task.delay") as mock_delay:
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = resp.json()["id"]
        mock_delay.assert_called_once_with(scan_id)

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/scans",
            json={"url": "https://example.com"},
        )
        assert resp.status_code == 401

    async def test_rejects_invalid_url(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            resp = await client.post(
                "/api/v1/scans",
                json={"url": "not-a-url"},
                headers=auth_headers,
            )
        assert resp.status_code == 422


class TestGetScan:
    async def test_returns_scan_by_id(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
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
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]

        creds = {"email": "other@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds)
        login_b = await client.post("/api/v1/auth/login", json=creds)
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_requires_auth_for_get(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
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
        with patch("app.api.v1.scans.run_scan_task.delay"):
            await client.post("/api/v1/scans", json={"url": "https://a.com"}, headers=auth_headers)
            await client.post("/api/v1/scans", json={"url": "https://b.com"}, headers=auth_headers)

        creds_b = {"email": "userb@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds_b)
        login_b = await client.post("/api/v1/auth/login", json=creds_b)
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
        with patch("app.api.v1.scans.run_scan_task.delay"):
            await client.post("/api/v1/scans", json={"url": "https://c.com"}, headers=headers_b)

        resp = await client.get("/api/v1/scans", headers=auth_headers)
        assert resp.status_code == 200
        scans = resp.json()
        assert len(scans) == 2
        urls = {s["url"].rstrip("/") for s in scans}
        assert urls == {"https://a.com", "https://b.com"}

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/scans")
        assert resp.status_code == 401


class TestScanStatus:
    async def test_returns_current_status(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]

        resp = await client.get(f"/api/v1/scans/{scan_id}/status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    async def test_requires_auth(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]
        resp = await client.get(f"/api/v1/scans/{scan_id}/status")
        assert resp.status_code == 401

    async def test_returns_404_for_unknown_scan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/scans/99999/status", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_403_for_other_users_scan(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]

        creds3 = {"email": "other3@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds3)
        login_b = await client.post("/api/v1/auth/login", json=creds3)
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        resp = await client.get(f"/api/v1/scans/{scan_id}/status", headers=headers_b)
        assert resp.status_code == 403


class TestScanSSE:
    async def test_sse_endpoint_returns_event_stream(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]

        # The event generator uses AsyncSessionLocal (module-level) to open
        # fresh DB sessions, bypassing the test's dependency override.
        # Stub it out so the generator returns a completed scan immediately.
        mock_scan = MagicMock()
        mock_scan.id = scan_id
        mock_scan.status = "completed"

        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session_local = MagicMock(return_value=mock_cm)

        with (
            patch("app.api.v1.scans.AsyncSessionLocal", mock_session_local),
            patch("app.api.v1.scans.get_scan_by_id", AsyncMock(return_value=mock_scan)),
        ):
            async with client.stream(
                "GET", f"/api/v1/scans/{scan_id}/events", headers=auth_headers
            ) as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]

    async def test_sse_requires_auth(self, client: AsyncClient, auth_headers: dict):
        with patch("app.api.v1.scans.run_scan_task.delay"):
            create = await client.post(
                "/api/v1/scans",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )
        scan_id = create.json()["id"]
        resp = await client.get(f"/api/v1/scans/{scan_id}/events")
        assert resp.status_code == 401
