"""
Integration tests for the scan diff route.

GET /api/v1/scans/diff?old={id1}&new={id2}
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan, Vulnerability


async def _create_scan_with_findings(
    db: AsyncSession, user_id: int, url: str, findings: list[tuple[str, str, str]]
) -> int:
    scan = Scan(user_id=user_id, url=url, status="completed")
    db.add(scan)
    await db.flush()
    for name, severity, evidence in findings:
        db.add(
            Vulnerability(
                scan_id=scan.id,
                name=name,
                severity=severity,
                description="",
                recommendation="",
                evidence=evidence,
            )
        )
    await db.commit()
    return scan.id


async def _user_id(client: AsyncClient, auth_headers: dict) -> int:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    return resp.json()["id"]


class TestScanDiff:
    async def test_diff_with_added_and_removed(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user_id = await _user_id(client, auth_headers)
        old_id = await _create_scan_with_findings(
            db_session,
            user_id,
            "https://example.com",
            [("Missing CSP", "high", ""), ("Old Issue", "low", "x")],
        )
        new_id = await _create_scan_with_findings(
            db_session,
            user_id,
            "https://example.com",
            [("Missing CSP", "high", ""), ("New Issue", "medium", "y")],
        )

        resp = await client.get(
            f"/api/v1/scans/diff?old={old_id}&new={new_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        added_names = [v["name"] for v in data["added"]]
        removed_names = [v["name"] for v in data["removed"]]
        unchanged_names = [v["name"] for v in data["unchanged"]]
        assert added_names == ["New Issue"]
        assert removed_names == ["Old Issue"]
        assert unchanged_names == ["Missing CSP"]

    async def test_empty_diff_when_scans_identical(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user_id = await _user_id(client, auth_headers)
        finds = [("Missing CSP", "high", "")]
        old_id = await _create_scan_with_findings(db_session, user_id, "https://x.com", finds)
        new_id = await _create_scan_with_findings(db_session, user_id, "https://x.com", finds)
        resp = await client.get(
            f"/api/v1/scans/diff?old={old_id}&new={new_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] == []
        assert data["removed"] == []
        assert len(data["unchanged"]) == 1

    async def test_returns_400_for_different_urls(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user_id = await _user_id(client, auth_headers)
        old_id = await _create_scan_with_findings(db_session, user_id, "https://a.com", [])
        new_id = await _create_scan_with_findings(db_session, user_id, "https://b.com", [])
        resp = await client.get(
            f"/api/v1/scans/diff?old={old_id}&new={new_id}", headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_returns_404_for_unknown_scan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/scans/diff?old=99998&new=99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_403_for_other_users_scan(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user_id = await _user_id(client, auth_headers)
        old_id = await _create_scan_with_findings(db_session, user_id, "https://x.com", [])
        new_id = await _create_scan_with_findings(db_session, user_id, "https://x.com", [])

        # Register a second user
        creds = {"email": "other_diff@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds)
        login = await client.post("/api/v1/auth/login", json=creds)
        headers_b = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = await client.get(f"/api/v1/scans/diff?old={old_id}&new={new_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/scans/diff?old=1&new=2")
        assert resp.status_code == 401

    async def test_diff_url_with_trailing_slash_is_normalized(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        user_id = await _user_id(client, auth_headers)
        old_id = await _create_scan_with_findings(db_session, user_id, "https://x.com/", [])
        new_id = await _create_scan_with_findings(db_session, user_id, "https://x.com", [])
        resp = await client.get(
            f"/api/v1/scans/diff?old={old_id}&new={new_id}", headers=auth_headers
        )
        assert resp.status_code == 200
