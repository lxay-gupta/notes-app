"""
Pytest fixtures for the entire test suite.

Database: async SQLAlchemy session backed by aiosqlite (in-memory SQLite).
  SQLite doesn't support all Postgres features used in migrations, so we
  create tables directly from Base.metadata instead of running Alembic.

Redis: a simple AsyncMock that tracks get/set/delete calls without
  requiring a running Redis instance.

HTTP client: AsyncClient hitting the FastAPI ASGI app with the DB and
  Redis dependencies overridden.
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base  # imports all models
from app.db.session import get_db
from app.db.redis import get_redis
from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine — created once per test session
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test transactional session — rolls back after each test."""
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Mock Redis — mirrors the async interface used by cache.py
# ---------------------------------------------------------------------------
class MockRedis:
    """
    Minimal in-memory Redis mock sufficient for testing cache get/set/delete
    and rate-limiting behaviour without a running Redis instance.
    """

    def __init__(self):
        self._store: dict = {}
        self._expires: dict = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value

    async def setex(self, key, ttl, value):
        self._store[key] = value
        self._expires[key] = ttl

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)

    async def ping(self):
        return True

    async def scan(self, cursor, match=None, count=100):
        import fnmatch
        keys = [k for k in self._store if (fnmatch.fnmatch(k, match) if match else True)]
        return 0, keys

    def pipeline(self):
        return MockPipeline(self)

    async def zremrangebyscore(self, key, min_score, max_score):
        return 0

    async def zcard(self, key):
        return 0

    async def zadd(self, key, mapping):
        return 1

    async def expire(self, key, ttl):
        return True


class MockPipeline:
    def __init__(self, redis: MockRedis):
        self._redis = redis
        self._ops = []

    async def zremrangebyscore(self, key, min_s, max_s):
        self._ops.append(("zremrangebyscore", key, min_s, max_s))
        return self

    async def zcard(self, key):
        self._ops.append(("zcard", key))
        return self

    async def zadd(self, key, mapping):
        self._ops.append(("zadd", key, mapping))
        return self

    async def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        # Return [None, 0, 1, True] — simulates: zrem=None, zcard=0 (no prior hits), zadd=1, expire=True
        return [None, 0, 1, True]


@pytest.fixture
def mock_redis():
    return MockRedis()


# ---------------------------------------------------------------------------
# Test app + HTTP client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(db_session, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with DB and Redis dependencies overridden to use
    the in-memory fixtures defined above.
    """
    def override_get_db():
        yield db_session

    def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Convenience helpers used across test modules
# ---------------------------------------------------------------------------
async def register_and_login(client: AsyncClient, email: str, password: str) -> dict:
    """Register a user and return the token dict from /auth/login."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
