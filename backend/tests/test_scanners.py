"""
Unit tests for HeadersScanner.

Strategy: mock the internal _fetch method so no real HTTP calls are made.
Each test verifies that a specific security header misconfiguration or absence
is correctly detected (or not detected on a clean site).
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.scanners.headers import HeadersScanner


SAFE_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=()",
}


def make_response(headers: dict) -> dict:
    """Helper: build a fake HTTP response dict."""
    return {"status": 200, "headers": headers, "body": ""}


class TestHeadersScannerMissingHeaders:
    async def test_detects_missing_csp(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "Content-Security-Policy"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Missing Content-Security-Policy" in names

    async def test_detects_missing_hsts(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "Strict-Transport-Security"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Missing Strict-Transport-Security" in names

    async def test_detects_missing_x_frame_options(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "X-Frame-Options"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Missing X-Frame-Options" in names

    async def test_detects_missing_x_content_type_options(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "X-Content-Type-Options"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Missing X-Content-Type-Options" in names

    async def test_detects_missing_referrer_policy(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "Referrer-Policy"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Missing Referrer-Policy" in names


class TestHeadersScannerMisconfigurations:
    async def test_csp_unsafe_inline_flagged(self):
        scanner = HeadersScanner()
        headers = {**SAFE_HEADERS, "Content-Security-Policy": "default-src 'self' 'unsafe-inline'"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Weak Content-Security-Policy" in names

    async def test_csp_unsafe_eval_flagged(self):
        scanner = HeadersScanner()
        headers = {**SAFE_HEADERS, "Content-Security-Policy": "default-src 'self' 'unsafe-eval'"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Weak Content-Security-Policy" in names

    async def test_hsts_short_max_age_flagged(self):
        scanner = HeadersScanner()
        headers = {**SAFE_HEADERS, "Strict-Transport-Security": "max-age=300"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        names = [f.name for f in findings]
        assert "Weak Strict-Transport-Security" in names


class TestHeadersScannerCleanSite:
    async def test_well_configured_site_has_no_findings(self):
        scanner = HeadersScanner()
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(SAFE_HEADERS))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == [], f"Expected no findings, got: {findings}"

    async def test_finding_has_required_fields(self):
        scanner = HeadersScanner()
        headers = {k: v for k, v in SAFE_HEADERS.items() if k != "Content-Security-Policy"}
        with patch.object(scanner, "_fetch", new=AsyncMock(return_value=make_response(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) >= 1
        finding = findings[0]
        assert hasattr(finding, "name")
        assert hasattr(finding, "severity")
        assert hasattr(finding, "description")
        assert finding.severity in ("info", "low", "medium", "high", "critical")
