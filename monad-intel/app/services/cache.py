"""Typed Redis helpers. Keep this module thin — no business logic."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        s = get_settings()
        _redis = Redis.from_url(s.redis_url, decode_responses=True)
    return _redis


def set_redis(r: Redis) -> None:
    """For tests: inject fakeredis."""
    global _redis
    _redis = r


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    r = get_redis()
    payload = value if isinstance(value, str) else json.dumps(value, default=str)
    if ttl_seconds is not None:
        await r.set(key, payload, ex=ttl_seconds)
    else:
        await r.set(key, payload)


async def cache_del(key: str) -> None:
    r = get_redis()
    await r.delete(key)
