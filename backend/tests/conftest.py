"""
Pytest configuration — test database (SQLite in-memory) + HTTP client.

Each test function gets:
- A fresh in-memory SQLite database (all models registered via app.db.models import).
- A FastAPI AsyncClient wired to that database via dependency override.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.db.models
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def engine():
    _engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest.fixture(scope="function")
async def client(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return Bearer auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "tester@example.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncSession:
    """Yield a raw async session for tests that bypass the HTTP client."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def registered_user(db_session: AsyncSession) -> dict:
    """Insert a user directly into the DB and return a dict with its fields."""
    user = User(
        email="recovery@test.com",
        password_hash="hashed",
        is_active=True,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {"id": user.id, "email": user.email}


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for all tests. Tests that specifically test rate
    limiting re-enable it locally inside the test body."""
    from app.core.limiter import limiter

    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original


@pytest.fixture(autouse=True)
def mock_email_send(monkeypatch):
    """Mock aiosmtplib.send so tests never try to hit a real SMTP server.

    Tests that specifically verify email behavior should re-mock locally.
    """
    import aiosmtplib

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(aiosmtplib, "send", _noop)
