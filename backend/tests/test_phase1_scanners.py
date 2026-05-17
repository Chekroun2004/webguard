"""
Unit tests for Phase 1 passive scanners — Étape 6.

Strategy: mock the scanner's fetchable method so no real HTTP/SSL calls are made.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.scanners.cookies import CookiesScanner
from app.scanners.http_methods import HttpMethodsScanner
from app.scanners.sensitive_files import SensitiveFilesScanner
from app.scanners.ssl_tls import SslTlsScanner
from app.scanners.technologies import TechnologiesScanner


def resp(headers: dict, cookies: list[str] | None = None) -> dict:
    return {"status": 200, "headers": headers, "set_cookies": cookies or [], "body": ""}


# ── CookiesScanner ────────────────────────────────────────────────────────────


class TestCookiesScanner:
    async def test_no_cookies_no_findings(self):
        scanner = CookiesScanner()
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp({}))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_missing_secure_flag(self):
        scanner = CookiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({}, ["session=abc; HttpOnly; SameSite=Lax"])),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Cookie Missing Secure Flag" for f in findings)

    async def test_missing_httponly_flag(self):
        scanner = CookiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({}, ["session=abc; Secure; SameSite=Lax"])),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Cookie Missing HttpOnly Flag" for f in findings)

    async def test_missing_samesite(self):
        scanner = CookiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({}, ["session=abc; Secure; HttpOnly"])),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Cookie Missing SameSite Attribute" for f in findings)

    async def test_samesite_none_without_secure(self):
        scanner = CookiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({}, ["session=abc; HttpOnly; SameSite=None"])),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Cookie SameSite=None Without Secure" for f in findings)

    async def test_well_configured_cookie_no_findings(self):
        scanner = CookiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp(
                {}, ["session=abc; Secure; HttpOnly; SameSite=Strict"]
            )),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_multiple_cookies_checked_individually(self):
        scanner = CookiesScanner()
        cookies = [
            "session=abc; Secure; HttpOnly; SameSite=Strict",
            "tracking=xyz",  # missing everything
        ]
        with patch.object(
            scanner, "_fetch", AsyncMock(return_value=resp({}, cookies))
        ):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Cookie Missing Secure Flag" in names
        assert "Cookie Missing HttpOnly Flag" in names


# ── SslTlsScanner ─────────────────────────────────────────────────────────────


def make_cert(days: int) -> dict:
    expiry = datetime.now(UTC) + timedelta(days=days)
    return {
        "notAfter": expiry.strftime("%b %d %H:%M:%S %Y GMT"),
        "subject": ((("commonName", "example.com"),),),
    }


class TestSslTlsScanner:
    async def test_tls_1_0_flagged_high(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1", "cert": make_cert(365), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Outdated TLS Version" in sevs
        assert sevs["Outdated TLS Version"] == "high"

    async def test_tls_1_1_flagged(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.1", "cert": make_cert(365), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Outdated TLS Version" for f in findings)

    async def test_tls_1_2_no_protocol_finding(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.2", "cert": make_cert(365), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        assert not any(f.name == "Outdated TLS Version" for f in findings)

    async def test_tls_1_3_clean(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.3", "cert": make_cert(365), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_cert_expiry_under_30_days_high(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.3", "cert": make_cert(10), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Certificate Expiring Soon" in sevs
        assert sevs["Certificate Expiring Soon"] == "high"

    async def test_cert_expiry_under_90_days_medium(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.3", "cert": make_cert(60), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Certificate Expiring Soon" in sevs
        assert sevs["Certificate Expiring Soon"] == "medium"

    async def test_cert_not_expiring_no_finding(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": "TLSv1.3", "cert": make_cert(180), "error": None}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_ssl_error_flagged(self):
        scanner = SslTlsScanner()
        ssl_info = {"version": None, "cert": None, "error": "CERTIFICATE_VERIFY_FAILED"}
        with patch.object(scanner, "_ssl_info", AsyncMock(return_value=ssl_info)):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "SSL/TLS Error" for f in findings)


# ── SensitiveFilesScanner ─────────────────────────────────────────────────────


class TestSensitiveFilesScanner:
    async def test_exposed_git_head_flagged(self):
        scanner = SensitiveFilesScanner()

        async def mock_check(url: str) -> int:
            return 200 if ".git" in url else 404

        with patch.object(scanner, "_check_path", side_effect=mock_check):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Exposed Sensitive File" for f in findings)
        assert any(".git" in f.evidence for f in findings)

    async def test_exposed_env_file_flagged(self):
        scanner = SensitiveFilesScanner()

        async def mock_check(url: str) -> int:
            return 200 if ".env" in url else 404

        with patch.object(scanner, "_check_path", side_effect=mock_check):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Exposed Sensitive File" for f in findings)

    async def test_all_404_no_findings(self):
        scanner = SensitiveFilesScanner()
        with patch.object(scanner, "_check_path", AsyncMock(return_value=404)):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_403_not_flagged(self):
        scanner = SensitiveFilesScanner()
        with patch.object(scanner, "_check_path", AsyncMock(return_value=403)):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_all_exposed_each_reported(self):
        scanner = SensitiveFilesScanner()
        with patch.object(scanner, "_check_path", AsyncMock(return_value=200)):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) >= 2


# ── TechnologiesScanner ───────────────────────────────────────────────────────


class TestTechnologiesScanner:
    async def test_server_with_version_medium(self):
        scanner = TechnologiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({"Server": "Apache/2.4.41 (Ubuntu)"})),
        ):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Server Version Disclosure" in sevs
        assert sevs["Server Version Disclosure"] == "medium"

    async def test_server_without_version_low(self):
        scanner = TechnologiesScanner()
        with patch.object(
            scanner, "_fetch", AsyncMock(return_value=resp({"Server": "nginx"}))
        ):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Server Version Disclosure" in sevs
        assert sevs["Server Version Disclosure"] == "low"

    async def test_x_powered_by_flagged(self):
        scanner = TechnologiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({"X-Powered-By": "PHP/8.1.0"})),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Technology Disclosure" for f in findings)

    async def test_aspnet_version_header_flagged(self):
        scanner = TechnologiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({"X-Aspnet-Version": "4.0.30319"})),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Technology Disclosure" for f in findings)

    async def test_no_disclosure_headers_no_findings(self):
        scanner = TechnologiesScanner()
        with patch.object(
            scanner, "_fetch",
            AsyncMock(return_value=resp({"Content-Type": "text/html"})),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []


# ── HttpMethodsScanner ────────────────────────────────────────────────────────


class TestHttpMethodsScanner:
    async def test_trace_flagged_high(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={"status": 200, "allow": "GET, POST, TRACE"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        sevs = {f.name: f.severity for f in findings}
        assert "Dangerous HTTP Method Enabled" in sevs
        assert sevs["Dangerous HTTP Method Enabled"] == "high"

    async def test_put_flagged_medium(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={"status": 200, "allow": "GET, POST, PUT"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Dangerous HTTP Method Enabled" for f in findings)

    async def test_delete_flagged(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={"status": 200, "allow": "GET, POST, DELETE"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Dangerous HTTP Method Enabled" for f in findings)

    async def test_safe_methods_no_findings(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={"status": 200, "allow": "GET, POST, HEAD, OPTIONS"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_options_405_no_crash(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={"status": 405, "allow": ""}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_multiple_dangerous_methods_each_reported(self):
        scanner = HttpMethodsScanner()
        with patch.object(
            scanner, "_options",
            AsyncMock(return_value={
                "status": 200, "allow": "GET, POST, TRACE, PUT, DELETE"
            }),
        ):
            findings = await scanner.scan("https://example.com", {})
        evidences = [f.evidence for f in findings]
        assert any("TRACE" in e for e in evidences)
        assert any("PUT" in e for e in evidences)
        assert any("DELETE" in e for e in evidences)
