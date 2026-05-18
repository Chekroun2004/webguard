"""
Unit tests for CorsScanner.

Strategy: mock _fetch so no real HTTP calls happen.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.scanners.cors import EVIL_ORIGIN, CorsScanner


def resp(headers: dict, status: int = 200) -> dict:
    return {"status": status, "headers": headers, "body": ""}


class TestCorsScanner:
    async def test_no_cors_headers_no_findings(self):
        scanner = CorsScanner()
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp({}))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_reflected_origin_with_credentials_high(self):
        scanner = CorsScanner()
        headers = {
            "Access-Control-Allow-Origin": EVIL_ORIGIN,
            "Access-Control-Allow-Credentials": "true",
        }
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].name == "CORS dangerously permissive"
        assert findings[0].severity == "high"

    async def test_wildcard_with_credentials_high(self):
        scanner = CorsScanner()
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].severity == "high"

    async def test_wildcard_without_credentials_medium(self):
        scanner = CorsScanner()
        headers = {"Access-Control-Allow-Origin": "*"}
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].name == "CORS wildcard origin"
        assert findings[0].severity == "medium"

    async def test_reflected_origin_without_credentials_medium(self):
        scanner = CorsScanner()
        headers = {"Access-Control-Allow-Origin": EVIL_ORIGIN}
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
        assert findings[0].name == "CORS reflects arbitrary origin"
        assert findings[0].severity == "medium"

    async def test_specific_allowed_origin_no_finding(self):
        """If the server returns its own trusted origin, that's normal."""
        scanner = CorsScanner()
        headers = {
            "Access-Control-Allow-Origin": "https://example.com",
            "Access-Control-Allow-Credentials": "true",
        }
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_credentials_case_insensitive(self):
        scanner = CorsScanner()
        headers = {
            "Access-Control-Allow-Origin": EVIL_ORIGIN,
            "Access-Control-Allow-Credentials": "TRUE",
        }
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert findings[0].severity == "high"

    async def test_header_lookup_is_case_insensitive(self):
        """Header keys can come back in any casing — scanner must normalize."""
        scanner = CorsScanner()
        headers = {"access-control-allow-origin": "*"}
        with patch.object(scanner, "_fetch", AsyncMock(return_value=resp(headers))):
            findings = await scanner.scan("https://example.com", {})
        assert len(findings) == 1
