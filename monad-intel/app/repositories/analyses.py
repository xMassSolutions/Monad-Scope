"""Analysis history repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import ContractAnalysis


async def insert(session: AsyncSession, analysis: ContractAnalysis) -> ContractAnalysis:
    session.add(analysis)
    await session.flush()
    return analysis


async def latest_for_contract(
    session: AsyncSession, contract_id: str
) -> ContractAnalysis | None:
    res = await session.execute(
        select(ContractAnalysis)
        .where(ContractAnalysis.contract_id == contract_id)
        .order_by(ContractAnalysis.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def history_for_contract(
    session: AsyncSession, contract_id: str, limit: int = 50
) -> list[ContractAnalysis]:
    res = await session.execute(
        select(ContractAnalysis)
        .where(ContractAnalysis.contract_id == contract_id)
        .order_by(ContractAnalysis.created_at.desc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def next_version(session: AsyncSession, contract_id: str) -> int:
    res = await session.execute(
        select(ContractAnalysis.analysis_version)
        .where(ContractAnalysis.contract_id == contract_id)
        .order_by(ContractAnalysis.analysis_version.desc())
        .limit(1)
    )
    last = res.scalar_one_or_none()
    return (last or 0) + 1
