"""Time helpers. UTC everywhere, no naive datetimes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def from_unix(ts: int | float) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def parse_hex_qty(value: str | int | None) -> int | None:
    """Parse Ethereum-style hex quantity ('0x10') or int. None passes through."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if v.startswith(("0x", "0X")):
            return int(v, 16)
        return int(v)
    raise TypeError(f"unsupported quantity type: {type(value).__name__}")


def add(seconds: float | int) -> datetime:
    return utc_now() + timedelta(seconds=seconds)


def hours(n: float | int) -> timedelta:
    return timedelta(hours=n)


def days(n: float | int) -> timedelta:
    return timedelta(days=n)


def is_stale(ts: datetime | None, ttl: timedelta) -> bool:
    if ts is None:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return utc_now() - ts > ttl
