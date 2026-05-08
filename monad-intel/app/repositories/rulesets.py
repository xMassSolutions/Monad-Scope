"""Rulesets repository — versioned scoring weights."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ruleset import Ruleset
from app.utils.time import utc_now


async def get_active(session: AsyncSession) -> Ruleset | None:
    res = await session.execute(
        select(Ruleset).where(Ruleset.status == "active").order_by(Ruleset.version.desc()).limit(1)
    )
    return res.scalar_one_or_none()


async def get_by_version(session: AsyncSession, version: int) -> Ruleset | None:
    res = await session.execute(select(Ruleset).where(Ruleset.version == version))
    return res.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Ruleset]:
    res = await session.execute(select(Ruleset).order_by(Ruleset.version.desc()))
    return list(res.scalars().all())


async def next_version(session: AsyncSession) -> int:
    res = await session.execute(
        select(Ruleset.version).order_by(Ruleset.version.desc()).limit(1)
    )
    last = res.scalar_one_or_none()
    return (last or 0) + 1


async def insert(
    session: AsyncSession,
    *,
    version: int,
    weights_json: dict[str, Any],
    metrics_json: dict[str, Any],
    status: str = "proposed",
) -> Ruleset:
    row = Ruleset(
        version=version,
        weights_json=weights_json,
        metrics_json=metrics_json,
        status=status,
        created_at=utc_now(),
    )
    session.add(row)
    await session.flush()
    return row


async def promote(session: AsyncSession, version: int) -> None:
    """Atomically promote a ruleset to `active` and archive the previous one."""
    await session.execute(update(Ruleset).where(Ruleset.status == "active").values(status="archived"))
    await session.execute(update(Ruleset).where(Ruleset.version == version).values(status="active"))
