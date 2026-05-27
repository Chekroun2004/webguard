"""Tests for authenticated scans — crypto, prepare_auth_cookies, propagation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

SCANS = "/api/v1/scans"


# ── crypto ────────────────────────────────────────────────────────────────────


class TestCrypto:
    def test_roundtrip(self):
        from app.core.crypto import decrypt_json, encrypt_json

        payload = {"strategy": "cookie", "name": "session", "value": "abc123"}
        ciphertext = encrypt_json(payload)
        assert ciphertext != "" and "session" not in ciphertext
        assert decrypt_json(ciphertext) == payload

    def test_tampered_ciphertext_raises(self):
        from app.core.crypto import DecryptionError, decrypt_json, encrypt_json

        ciphertext = encrypt_json({"x": 1})
        with pytest.raises(DecryptionError):
            decrypt_json(ciphertext[:-1] + ("A" if ciphertext[-1] != "A" else "B"))


# ── prepare_auth_cookies ──────────────────────────────────────────────────────


class TestPrepareAuthCookies:
    async def test_cookie_strategy_returns_dict(self):
        from app.services.scan_auth import prepare_auth_cookies

        cookies = await prepare_auth_cookies(
            {"strategy": "cookie", "name": "session", "value": "abc"}
        )
        assert cookies == {"session": "abc"}

    async def test_none_returns_empty(self):
        from app.services.scan_auth import prepare_auth_cookies

        assert await prepare_auth_cookies(None) == {}
        assert await prepare_auth_cookies({}) == {}

    async def test_form_login_captures_session_cookie(self):
        from app.services.scan_auth import prepare_auth_cookies

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_session.cookies = {"session_id": "logged-in"}

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scan_auth.httpx.AsyncClient", return_value=mock_cm):
            cookies = await prepare_auth_cookies(
                {
                    "strategy": "form_login",
                    "login_url": "https://target/login",
                    "username_field": "email",
                    "password_field": "password",
                    "username": "u",
                    "password": "p",
                }
            )

        assert cookies == {"session_id": "logged-in"}
        mock_session.post.assert_awaited_once()
        call_args = mock_session.post.call_args
        assert call_args.args[0] == "https://target/login"
        assert call_args.kwargs["data"] == {"email": "u", "password": "p"}

    async def test_form_login_swallows_errors(self):
        from app.services.scan_auth import prepare_auth_cookies

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=Exception("network down"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scan_auth.httpx.AsyncClient", return_value=mock_cm):
            cookies = await prepare_auth_cookies(
                {
                    "strategy": "form_login",
                    "login_url": "https://target/login",
                    "username_field": "u",
                    "password_field": "p",
                    "username": "x",
                    "password": "y",
                }
            )

        assert cookies == {}


# ── ScanCreate persists encrypted blob ────────────────────────────────────────


class TestScanCreateEncryptsAuthConfig:
    async def test_no_auth_config_stores_null(self, client: AsyncClient, auth_headers: dict):
        from app.db.models.scan import Scan

        resp = await client.post(
            SCANS,
            json={"url": "https://example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        scan_id = resp.json()["id"]

        # Read via the same app engine the test client uses
        from app.api.deps import get_db
        from app.main import app

        override = app.dependency_overrides[get_db]
        async for session in override():
            scan = (await session.execute(select(Scan).where(Scan.id == scan_id))).scalar_one()
            assert scan.auth_config_encrypted is None
            return  # generator yields once

    async def test_cookie_auth_config_stored_encrypted(
        self, client: AsyncClient, auth_headers: dict
    ):
        from app.core.crypto import decrypt_json
        from app.db.models.scan import Scan

        resp = await client.post(
            SCANS,
            json={
                "url": "https://example.com",
                "auth_config": {
                    "strategy": "cookie",
                    "name": "session",
                    "value": "secret-token",
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202
        scan_id = resp.json()["id"]

        from app.api.deps import get_db
        from app.main import app

        override = app.dependency_overrides[get_db]
        async for session in override():
            scan = (await session.execute(select(Scan).where(Scan.id == scan_id))).scalar_one()
            assert scan.auth_config_encrypted is not None
            # Ciphertext must not leak the plaintext
            assert "secret-token" not in scan.auth_config_encrypted
            assert decrypt_json(scan.auth_config_encrypted) == {
                "strategy": "cookie",
                "name": "session",
                "value": "secret-token",
            }
            return

    async def test_invalid_auth_strategy_rejected(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            SCANS,
            json={
                "url": "https://example.com",
                "auth_config": {"strategy": "ldap", "name": "x", "value": "y"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── execute_scan propagates cookies into scanner config ───────────────────────


class TestExecuteScanPropagatesCookies:
    async def test_passive_scanners_receive_cookies(self, db_session, registered_user):
        from app.core.crypto import encrypt_json
        from app.db.models.scan import Scan
        from app.workers.tasks import scan as scan_task

        # Persist a scan with an encrypted cookie auth_config
        scan = Scan(
            user_id=registered_user["id"],
            url="https://example.com",
            status="pending",
            auth_config_encrypted=encrypt_json(
                {"strategy": "cookie", "name": "session", "value": "tok"}
            ),
        )
        db_session.add(scan)
        await db_session.commit()
        await db_session.refresh(scan, ["vulnerabilities"])

        captured: list[dict] = []

        class FakeScanner:
            def __init__(self):
                pass

            async def scan(self, url: str, config: dict):
                captured.append(config)
                return []

        # Swap both scanner lists with our spy class to avoid network calls.
        with (
            patch.object(scan_task, "SCANNERS", [FakeScanner]),
            patch.object(scan_task, "ACTIVE_SCANNERS", []),
            patch.object(scan_task.Crawler, "crawl", AsyncMock(return_value=[])),
        ):
            await scan_task.execute_scan(scan.id, db_session)

        assert captured, "scanner was not invoked"
        assert captured[0].get("cookies") == {"session": "tok"}
