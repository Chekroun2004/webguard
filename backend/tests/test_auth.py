"""
Auth routes test suite — written before implementation (TDD).

Covers: register, login, refresh, me — happy paths and error cases.
"""
import pytest
from httpx import AsyncClient

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
ME = "/api/v1/auth/me"

ALICE = {"email": "alice@example.com", "password": "securepass1", "full_name": "Alice Dupont"}


# ── shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
async def alice(client: AsyncClient) -> dict:
    resp = await client.post(REGISTER, json=ALICE)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
async def tokens(client: AsyncClient, alice: dict) -> dict:
    resp = await client.post(LOGIN, json={"email": ALICE["email"], "password": ALICE["password"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── register ─────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_creates_user_and_returns_profile(self, client: AsyncClient) -> None:
        resp = await client.post(REGISTER, json=ALICE)

        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == ALICE["email"]
        assert data["full_name"] == ALICE["full_name"]
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    async def test_password_is_never_returned(self, client: AsyncClient) -> None:
        resp = await client.post(REGISTER, json=ALICE)

        body = resp.text
        assert "securepass1" not in body
        assert "password_hash" not in body

    async def test_duplicate_email_returns_400(self, client: AsyncClient, alice: dict) -> None:
        resp = await client.post(REGISTER, json=ALICE)
        assert resp.status_code == 400

    async def test_short_password_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(REGISTER, json={**ALICE, "password": "short"})
        assert resp.status_code == 422

    async def test_invalid_email_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(REGISTER, json={**ALICE, "email": "not-an-email"})
        assert resp.status_code == 422

    async def test_missing_email_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(REGISTER, json={"password": "securepass1"})
        assert resp.status_code == 422


# ── login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_returns_access_and_refresh_tokens(
        self, client: AsyncClient, alice: dict
    ) -> None:
        resp = await client.post(
            LOGIN, json={"email": ALICE["email"], "password": ALICE["password"]}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password_returns_401(self, client: AsyncClient, alice: dict) -> None:
        resp = await client.post(
            LOGIN, json={"email": ALICE["email"], "password": "wrongpassword"}
        )
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            LOGIN, json={"email": "nobody@example.com", "password": "securepass1"}
        )
        assert resp.status_code == 401

    async def test_missing_fields_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(LOGIN, json={"email": ALICE["email"]})
        assert resp.status_code == 422


# ── refresh ───────────────────────────────────────────────────────────────────

class TestRefresh:
    async def test_returns_new_token_pair(self, client: AsyncClient, tokens: dict) -> None:
        resp = await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_garbage_token_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(REFRESH, json={"refresh_token": "not.a.valid.jwt"})
        assert resp.status_code == 401

    async def test_access_token_rejected_as_refresh(
        self, client: AsyncClient, tokens: dict
    ) -> None:
        # Security: access tokens must not be usable as refresh tokens
        resp = await client.post(REFRESH, json={"refresh_token": tokens["access_token"]})
        assert resp.status_code == 401


# ── me ────────────────────────────────────────────────────────────────────────

class TestMe:
    async def test_returns_current_user(self, client: AsyncClient, tokens: dict) -> None:
        resp = await client.get(ME, headers={"Authorization": f"Bearer {tokens['access_token']}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == ALICE["email"]
        assert "password" not in data
        assert "password_hash" not in data

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get(ME)
        assert resp.status_code == 401

    async def test_malformed_token_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get(ME, headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    async def test_refresh_token_rejected_as_access(
        self, client: AsyncClient, tokens: dict
    ) -> None:
        # Security: refresh tokens must not grant access to protected routes
        resp = await client.get(
            ME, headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
        )
        assert resp.status_code == 401
