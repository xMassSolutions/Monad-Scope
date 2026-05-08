"""Public case library."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import contracts as contracts_repo
from app.schemas.contract import ContractRead

router = APIRouter()


@router.get("/library/recent", response_model=list[ContractRead])
async def recent(
    limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)
) -> list[ContractRead]:
    rows = await contracts_repo.list_recent(session, limit=limit, offset=offset)
    return [ContractRead.model_validate(r) for r in rows]


@router.get("/library/high-risk", response_model=list[ContractRead])
async def high_risk(
    limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)
) -> list[ContractRead]:
    rows = await contracts_repo.list_high_risk(session, limit=limit, offset=offset)
    return [ContractRead.model_validate(r) for r in rows]
