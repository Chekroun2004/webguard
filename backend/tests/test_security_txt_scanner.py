"""
Unit tests for SecurityTxtScanner.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.scanners.security_txt import SecurityTxtScanner


def resp(status: int, body: str = "", url: str = "https://example.com/.well-known/security.txt"):
    return {"status": status, "headers": {}, "body": body, "url": url}


class TestSecurityTxtScanner:
    async def test_missing_returns_info_finding(self):
        scanner = SecurityTxtScanner()
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(404))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].name == "Missing /.well-known/security.txt"
        assert findings[0].severity == "info"

    async def test_empty_body_returns_low_finding(self):
        scanner = SecurityTxtScanner()
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(200, ""))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].name == "Incomplete security.txt"
        assert findings[0].severity == "low"

    async def test_missing_contact_field_returns_low(self):
        scanner = SecurityTxtScanner()
        body = "Expires: 2030-01-01T00:00:00Z\nPolicy: https://example.com/policy"
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(200, body))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].severity == "low"

    async def test_valid_security_txt_no_finding(self):
        scanner = SecurityTxtScanner()
        body = "Contact: mailto:security@example.com\n" "Expires: 2030-01-01T00:00:00Z\n"
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(200, body))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_contact_case_insensitive(self):
        scanner = SecurityTxtScanner()
        body = "CONTACT: mailto:security@example.com\n"
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(200, body))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_403_treated_as_missing(self):
        scanner = SecurityTxtScanner()
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(403))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].severity == "info"

    async def test_network_error_silent(self):
        scanner = SecurityTxtScanner()
        with patch.object(scanner, "_fetch", AsyncMock(side_effect=Exception("boom"))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []
