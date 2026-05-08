"""Distributed locks via Redis (SET NX PX) and Postgres advisory locks."""

from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator

from redis.asyncio import Redis

# Lua script for atomic compare-and-delete (release token-owned lock).
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
else
  return 0
end
"""


class LockNotAcquired(Exception):
    pass


class RedisLock:
    """Token-owned single-acquire Redis lock.

    Use `acquire(blocking=...)` and `release()` directly, or the
    `redis_lock(...)` async context manager below.
    """

    def __init__(self, redis: Redis, key: str, ttl_ms: int = 60_000) -> None:
        self.redis = redis
        self.key = key
        self.ttl_ms = ttl_ms
        self._token: str | None = None

    async def acquire(self, blocking: float = 0.0, retry_interval: float = 0.05) -> bool:
        deadline = asyncio.get_event_loop().time() + blocking
        while True:
            token = secrets.token_hex(16)
            ok = await self.redis.set(self.key, token, nx=True, px=self.ttl_ms)
            if ok:
                self._token = token
                return True
            if blocking <= 0 or asyncio.get_event_loop().time() >= deadline:
                return False
            await asyncio.sleep(retry_interval)

    async def release(self) -> bool:
        if self._token is None:
            return False
        try:
            res = await self.redis.eval(_RELEASE_SCRIPT, 1, self.key, self._token)
            return bool(res)
        finally:
            self._token = None


@asynccontextmanager
async def redis_lock(
    redis: Redis,
    key: str,
    ttl_ms: int = 60_000,
    blocking: float = 0.0,
) -> AsyncIterator[bool]:
    """Yields True if acquired, False otherwise. Always releases on exit."""
    lock = RedisLock(redis, key, ttl_ms)
    acquired = await lock.acquire(blocking=blocking)
    try:
        yield acquired
    finally:
        if acquired:
            await lock.release()


# ---------------- Postgres advisory locks ----------------

import hashlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _advisory_key(name: str) -> int:
    """Map an arbitrary string to a signed bigint for pg_advisory_lock."""
    digest = hashlib.blake2b(name.encode("utf-8"), digest_size=8).digest()
    val = int.from_bytes(digest, "big", signed=False)
    # Convert to signed 64-bit range.
    if val >= 1 << 63:
        val -= 1 << 64
    return val


@asynccontextmanager
async def pg_advisory_lock(session: AsyncSession, name: str) -> AsyncIterator[None]:
    """Postgres transaction-scoped advisory lock. No-op on non-Postgres backends."""
    bind = session.bind
    if bind is not None and bind.dialect.name != "postgresql":
        # Advisory locks are PG-only. Other dialects: best-effort no-op.
        yield
        return
    key = _advisory_key(name)
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
    yield
