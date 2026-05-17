"""
Integration tests for scan report routes — Étape 8.

GET /api/v1/scans/{id}/report      → JSON report
GET /api/v1/scans/{id}/report.pdf  → PDF download
"""

from unittest.mock import patch

from httpx import AsyncClient


async def _create_completed_scan(client: AsyncClient, auth_headers: dict) -> int:
    """Create a scan, mark it completed with one finding, return scan_id."""
    with patch("app.api.v1.scans.run_scan_task.delay"):
        resp = await client.post(
            "/api/v1/scans",
            json={"url": "https://example.com"},
            headers=auth_headers,
        )
    return resp.json()["id"]


class TestScanReportJson:
    async def test_returns_json_structure(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        resp = await client.get(f"/api/v1/scans/{scan_id}/report", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scan_id"] == scan_id
        assert "url" in data
        assert "status" in data
        assert "generated_at" in data
        assert "summary" in data
        assert "findings" in data

    async def test_summary_contains_severity_counts(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        resp = await client.get(f"/api/v1/scans/{scan_id}/report", headers=auth_headers)
        summary = resp.json()["summary"]
        for key in ("total", "critical", "high", "medium", "low", "info"):
            assert key in summary, f"Missing key: {key}"

    async def test_findings_have_required_fields(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        resp = await client.get(f"/api/v1/scans/{scan_id}/report", headers=auth_headers)
        for finding in resp.json()["findings"]:
            for field in ("name", "severity", "description", "recommendation", "evidence"):
                assert field in finding, f"Missing field: {field}"

    async def test_requires_auth(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        resp = await client.get(f"/api/v1/scans/{scan_id}/report")
        assert resp.status_code == 401

    async def test_returns_404_for_unknown_scan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/scans/99999/report", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_403_for_other_users_scan(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        creds = {"email": "rpt_other@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds)
        login = await client.post("/api/v1/auth/login", json=creds)
        headers_b = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = await client.get(f"/api/v1/scans/{scan_id}/report", headers=headers_b)
        assert resp.status_code == 403


class TestScanReportPdf:
    async def test_returns_pdf_content_type(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        with patch("app.api.v1.reports.HTML") as mock_html:
            mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
            resp = await client.get(f"/api/v1/scans/{scan_id}/report.pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    async def test_pdf_has_content_disposition_attachment(
        self, client: AsyncClient, auth_headers: dict
    ):
        scan_id = await _create_completed_scan(client, auth_headers)
        with patch("app.api.v1.reports.HTML") as mock_html:
            mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
            resp = await client.get(f"/api/v1/scans/{scan_id}/report.pdf", headers=auth_headers)
        assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_pdf_requires_auth(self, client: AsyncClient, auth_headers: dict):
        scan_id = await _create_completed_scan(client, auth_headers)
        resp = await client.get(f"/api/v1/scans/{scan_id}/report.pdf")
        assert resp.status_code == 401

    async def test_pdf_returns_404_for_unknown_scan(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/scans/99999/report.pdf", headers=auth_headers)
        assert resp.status_code == 404

    async def test_pdf_returns_403_for_other_users_scan(
        self, client: AsyncClient, auth_headers: dict
    ):
        scan_id = await _create_completed_scan(client, auth_headers)
        creds = {"email": "pdfother@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=creds)
        login = await client.post("/api/v1/auth/login", json=creds)
        headers_b = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = await client.get(f"/api/v1/scans/{scan_id}/report.pdf", headers=headers_b)
        assert resp.status_code == 403
