"""Findings repository."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ContractFinding


async def replace_findings(
    session: AsyncSession, contract_id: str, findings: list[ContractFinding]
) -> None:
    """Atomically replace the finding set for a contract."""
    await session.execute(delete(ContractFinding).where(ContractFinding.contract_id == contract_id))
    for f in findings:
        f.contract_id = contract_id
        session.add(f)
    await session.flush()


async def list_for_contract(session: AsyncSession, contract_id: str) -> list[ContractFinding]:
    res = await session.execute(
        select(ContractFinding)
        .where(ContractFinding.contract_id == contract_id)
        .order_by(ContractFinding.weight.desc(), ContractFinding.code.asc())
    )
    return list(res.scalars().all())
