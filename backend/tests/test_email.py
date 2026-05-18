"""
Unit tests for app.services.email.

We don't want these tests to hit a real SMTP server — we override the autouse
mock with our own AsyncMock so we can inspect the sent message.
"""

from unittest.mock import AsyncMock

import pytest

from app.db.models.scan import Scan, Vulnerability
from app.services import email as email_service


def _make_scan() -> Scan:
    return Scan(id=42, user_id=1, url="https://example.com", status="completed")


@pytest.fixture
def captured_send(monkeypatch):
    """Capture the EmailMessage sent via aiosmtplib.send."""
    import aiosmtplib

    mock = AsyncMock()
    monkeypatch.setattr(aiosmtplib, "send", mock)
    return mock


class TestSendScanCompleteEmail:
    async def test_sends_with_expected_fields(self, captured_send):
        scan = _make_scan()
        findings = [
            Vulnerability(
                scan_id=42,
                name="Missing CSP",
                severity="high",
                description="",
                recommendation="",
                evidence="",
            ),
        ]
        ok = await email_service.send_scan_complete_email(
            user_email="user@gmail.com",
            user_name="Alice",
            scan=scan,
            findings=findings,
        )
        assert ok is True
        assert captured_send.await_count == 1
        message = captured_send.await_args.args[0]
        assert message["To"] == "user@gmail.com"
        assert "Scan terminé" in message["Subject"]
        assert "https://example.com" in message["Subject"]

    async def test_skips_when_notifications_disabled(self, captured_send, monkeypatch):
        from app.services import email as svc

        monkeypatch.setattr(svc.settings, "email_notifications_enabled", False)
        scan = _make_scan()
        ok = await svc.send_scan_complete_email("u@gmail.com", None, scan, [])
        assert ok is False
        assert captured_send.await_count == 0

    async def test_swallows_smtp_errors(self, monkeypatch):
        import aiosmtplib

        async def _raises(*args, **kwargs):
            raise aiosmtplib.SMTPException("connection refused")

        monkeypatch.setattr(aiosmtplib, "send", _raises)
        scan = _make_scan()
        ok = await email_service.send_scan_complete_email("u@gmail.com", None, scan, [])
        assert ok is False  # never raises

    async def test_summary_counts_match_findings(self, captured_send):
        scan = _make_scan()
        findings = [
            Vulnerability(
                scan_id=42,
                name="A",
                severity="critical",
                description="",
                recommendation="",
                evidence="",
            ),
            Vulnerability(
                scan_id=42,
                name="B",
                severity="critical",
                description="",
                recommendation="",
                evidence="",
            ),
            Vulnerability(
                scan_id=42, name="C", severity="low", description="", recommendation="", evidence=""
            ),
        ]
        await email_service.send_scan_complete_email("u@gmail.com", None, scan, findings)
        message = captured_send.await_args.args[0]
        # 3 vulnerabilities total — check it's in the subject
        assert "3 vulnérabilité" in message["Subject"]
