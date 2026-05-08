"""Contract API routes — the public case-library entry point."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import analyses as analyses_repo
from app.repositories import contracts as contracts_repo
from app.repositories import findings as findings_repo
from app.schemas.analysis import AnalysisRead, FindingRead
from app.schemas.contract import ContractFull, ContractRead
from app.services import enrichment as enrichment_svc
from app.services import prime_state
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier

router = APIRouter()


def _normalize(address: str) -> str:
    address = address.lower()
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(400, detail="invalid address")
    return address


@router.get("/contracts/{address}", response_model=ContractFull)
async def get_contract(address: str, session: AsyncSession = Depends(get_session)) -> ContractFull:
    address = _normalize(address)
    c = await contracts_repo.get_by_address(session, address)
    if c is None:
        raise HTTPException(404, detail="contract not found")
    sf = await contracts_repo.get_static_features(session, c.id)
    df = await contracts_repo.get_dynamic_features(session, c.id)
    fs = await findings_repo.list_for_contract(session, c.id)
    latest = await analyses_repo.latest_for_contract(session, c.id)
    prime = await prime_state.assemble_status_block(session, c)
    return ContractFull(
        contract=ContractRead.model_validate(c),
        static_features=sf,
        dynamic_features=df,
        findings=[FindingRead.model_validate(f) for f in fs],
        latest_analysis=AnalysisRead.model_validate(latest) if latest else None,
        prime=prime,
    )


@router.get("/contracts/{address}/findings", response_model=list[FindingRead])
async def get_findings(address: str, session: AsyncSession = Depends(get_session)) -> list[FindingRead]:
    address = _normalize(address)
    c = await contracts_repo.get_by_address(session, address)
    if c is None:
        raise HTTPException(404, detail="contract not found")
    fs = await findings_repo.list_for_contract(session, c.id)
    return [FindingRead.model_validate(f) for f in fs]


@router.get("/contracts/{address}/history", response_model=list[AnalysisRead])
async def get_history(
    address: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[AnalysisRead]:
    address = _normalize(address)
    c = await contracts_repo.get_by_address(session, address)
    if c is None:
        raise HTTPException(404, detail="contract not found")
    rows = await analyses_repo.history_for_contract(session, c.id, limit=limit)
    return [AnalysisRead.model_validate(a) for a in rows]


@router.post("/contracts/{address}/analyze", response_model=ContractFull)
async def analyze_now(address: str, session: AsyncSession = Depends(get_session)) -> ContractFull:
    """Trigger an immediate refresh — re-run the free pipeline."""
    address = _normalize(address)
    c = await contracts_repo.get_by_address(session, address)
    if c is None:
        raise HTTPException(404, detail="contract not found")
    rpc = JsonRpcClient()
    verifier = Verifier()
    try:
        await enrichment_svc.enrich_contract(session, rpc, verifier, c, stage="refined")
        await session.commit()
    finally:
        await rpc.close()
    return await get_contract(address, session=session)
