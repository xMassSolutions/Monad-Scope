"""Prime analysis cache repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prime import PrimeAnalysis


async def get_by_implementation_hash(
    session: AsyncSession, impl_hash: str
) -> PrimeAnalysis | None:
    res = await session.execute(
        select(PrimeAnalysis)
        .where(PrimeAnalysis.implementation_hash == impl_hash)
        .order_by(PrimeAnalysis.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_by_contract_id(session: AsyncSession, contract_id: str) -> PrimeAnalysis | None:
    res = await session.execute(
        select(PrimeAnalysis)
        .where(PrimeAnalysis.contract_id == contract_id)
        .order_by(PrimeAnalysis.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def insert(session: AsyncSession, row: PrimeAnalysis) -> PrimeAnalysis:
    session.add(row)
    await session.flush()
    return row
