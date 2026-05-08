"""Job queue repository (DB-backed; the Redis lock prevents the race)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.utils.ids import new_id
from app.utils.time import utc_now


ACTIVE_STATUSES = ("queued", "running")


async def find_active(
    session: AsyncSession, *, kind: str, dedup_key: str
) -> Job | None:
    res = await session.execute(
        select(Job)
        .where(
            Job.kind == kind,
            Job.dedup_key == dedup_key,
            Job.status.in_(ACTIVE_STATUSES),
        )
        .limit(1)
    )
    return res.scalar_one_or_none()


async def create_if_absent(
    session: AsyncSession,
    *,
    kind: str,
    dedup_key: str | None,
    payload: dict[str, Any],
) -> Job | None:
    """Insert a queued job. Returns None if a unique-constraint conflict occurs
    (i.e., another active job already exists for this (kind, dedup_key))."""
    now = utc_now()
    job = Job(
        id=new_id(),
        kind=kind,
        status="queued",
        active_marker=1,
        dedup_key=dedup_key,
        payload=payload,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return None
    return job


async def mark_running(session: AsyncSession, job_id: str) -> None:
    now = utc_now()
    await session.execute(
        update(Job).where(Job.id == job_id).values(status="running", started_at=now, updated_at=now)
    )


async def mark_done(
    session: AsyncSession, job_id: str, result: dict[str, Any] | None = None
) -> None:
    now = utc_now()
    await session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status="done",
            active_marker=None,
            result=result or {},
            finished_at=now,
            updated_at=now,
        )
    )


async def mark_failed(session: AsyncSession, job_id: str, error: str) -> None:
    now = utc_now()
    await session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status="failed",
            active_marker=None,
            error=error[:2000],
            finished_at=now,
            updated_at=now,
        )
    )


async def get(session: AsyncSession, job_id: str) -> Job | None:
    res = await session.execute(select(Job).where(Job.id == job_id))
    return res.scalar_one_or_none()
