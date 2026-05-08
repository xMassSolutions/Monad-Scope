"""Shared fixtures: in-memory sqlite + fakeredis. No Postgres or Redis required."""

from __future__ import annotations

import os
from typing import AsyncIterator

import fakeredis.aioredis
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Force a clean sqlite DB and dev env BEFORE app imports.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_ENV", "dev")

from app.config import get_settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.services import cache as cache_svc  # noqa: E402


@pytest_asyncio.fixture
async def db():
    """Per-test in-memory SQLite engine shared across sessions via StaticPool."""
    get_settings.cache_clear()  # type: ignore[attr-defined]

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    # Patch the global engine + session factory so app code uses our engine.
    import app.db as db_mod

    db_mod._engine = engine  # type: ignore[attr-defined]
    db_mod._session_factory = async_sessionmaker(  # type: ignore[attr-defined]
        bind=engine, expire_on_commit=False, autoflush=False,
    )

    async with engine.begin() as conn:
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield db_mod._session_factory  # type: ignore[attr-defined]
    finally:
        await engine.dispose()
        db_mod._engine = None  # type: ignore[attr-defined]
        db_mod._session_factory = None  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    cache_svc.set_redis(r)
    yield r
    await r.flushall()
    await r.aclose()
