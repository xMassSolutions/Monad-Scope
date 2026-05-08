"""Outcomes repository."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outcome import Outcome
from app.utils.time import utc_now


async def insert(
    session: AsyncSession,
    *,
    contract_id: str | None,
    project_id: str | None,
    outcome_label: str,
    notes: str | None = None,
) -> Outcome:
    now = utc_now()
    row = Outcome(
        contract_id=contract_id,
        project_id=project_id,
        outcome_label=outcome_label,
        notes=notes,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return row


async def list_in_window(
    session: AsyncSession, since: datetime
) -> list[Outcome]:
    res = await session.execute(
        select(Outcome).where(Outcome.created_at >= since).order_by(Outcome.created_at.asc())
    )
    return list(res.scalars().all())


async def for_contract(session: AsyncSession, contract_id: str) -> list[Outcome]:
    res = await session.execute(
        select(Outcome)
        .where(Outcome.contract_id == contract_id)
        .order_by(Outcome.created_at.asc())
    )
    return list(res.scalars().all())
